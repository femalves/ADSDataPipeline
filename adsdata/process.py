
import sys
import traceback

from adsmsg import NonBibRecord, MetricsRecord
from adsdata import diffs, metrics, tasks, reader, aggregator
from adsdata.memory_cache import Refereed, ReferenceNetwork, CitationNetwork

from adsdata.file_defs import data_files

# read data for the current bibcode from all the files
# generate a complete nonbib record
# send it to master
# generate a complete metrics record
# send it to master

app = tasks.app
logger = tasks.app.logger
nonbib_keys = data_files.keys()


def test_process(compute_metrics=True):
    agg = aggregator.TestAggregator()
    agg.open_all()
    count = 0
    s = agg.read_next()
    while s:
        try:
            if count % 100 == 0:
                logger.info('process, count = {}, line = {}'.format(count, s[:40]))
            s = agg.read_next()
            count = count + 1
            if s is None:
                break
        except:
            e = sys.exc_info()[0]
            logger.error('Error! perhaps while processing line: {}, error: {}'.format(s[:40], str(e)))
                 

def process(compute_metrics=True):
    # keep reading one (logical) line from each file
    # generate nonbib and metrics record
    
    open_all(root_dir=app.conf.get('INPUT_DATA_ROOT', './adsdata/tests/data1/config/'))
    count = 0
    # skip_lines(100000)
    d = read_next()
    while (d is not None):
        try:
            # process it
            bibcode = d['canonical']
            if count % 100 == 0:
                logger.info('processing, count = {}, current bibcode = {}'.format(count, bibcode))
            if len(bibcode) == 0:
                print('no bibcode, exiting main loop')
                break
            if not app.conf.get('TEST_NO_PROCESSING', False):
                rec = convert(d)
                nonbib = NonBibRecord(**rec)
            if compute_metrics:
                met = metrics.compute_metrics(d)
                met_proto = MetricsRecord(**met)
                if count % 100 == 0:
                    logger.info('met = {}'.format(met))
            d = read_next()
            if app.conf.get('TEST_MAX_ROWS', -1) > 0:
                if app.conf['TEST_MAX_ROWS'] >= count:
                    break  # useful during testing
            count += 1
        except AttributeError as e:
            logger.error('AttributeError while processing bibcode: {}, error: {}'.format(d['canonical'], str(e)))
            logger.error(traceback.format_exc())
        except:
            e = sys.exc_info()[0]
            logger.error('Error! perhaps while processing bibcode: {}, error: {}'.format(d['canonical'], str(e)))


def process_bibcodes(bibcodes, compute_metrics=True):
    """this funciton is useful when debugging"""
    open_all(root_dir=app.conf.get('INPUT_DATA_ROOT', './adsdata/tests/data1/config/'))
    for bibcode in bibcodes:
        nonbib = read_next_bibcode(bibcode)
        logger.info('bibcode: {}, nonbib: {}'.format(bibcode, nonbib))
        converted = convert(nonbib)
        logger.info('bibcode: {}, nonbib converted: {}'.format(bibcode, converted))
        nonbib_proto = NonBibRecord(**converted)
        logger.info('bibcode: {}, nonbib protobuf: {}'.format(bibcode, nonbib_proto))
        if compute_metrics:
            met = metrics.compute_metrics(nonbib)
            logger.info('bibcode: {}, metrics: {}'.format(bibcode, met))
            met_proto = MetricsRecord(**met)
            logger.info('bibcode: {}, metrics protobuf: {}'.format(bibcode, met_proto))


def convert(passed):
    """convert full nonbib dict to what is needed for nonbib protobuf

    data links values are read from separate files so they are in separate dicts
        they must be merged into one field for the protobuf
    a couple fields are summarized
    some other fields are just copied
    some fields are deleted
    """
    return_value = {}
    return_value['data_links_rows'] = []
    return_value['property'] = set()
    return_value['esource'] = set()
    for filetype, value in passed.items():
        file_properties = data_files[filetype]
        if filetype == 'canonical':
            return_value['bibcode'] = passed['canonical']
        elif ('extra_values' in file_properties and 'link_type' in file_properties['extra_values'] and value != file_properties['default_value']):
            # here with one or more real datalinks value(s)
            # add each data links dict to existing list of dicts
            # tweak some values (e.g., sub_link_type) in original dict
            if type(value) is bool or type(value) is dict:
                d = convert_data_link(filetype, value)
                return_value['data_links_rows'].append(d)
            elif type(value) is list:
                for v in value:
                    d = convert_data_link(filetype, v)
                    return_value['data_links_rows'].append(d)
            else:
                print('!!! error in process.convert with {} {} {}'.format(filetype, type(value), value))
            
            if file_properties['extra_values']['link_type'] == 'ESOURCE':
                return_value['esource'].add(file_properties['extra_values']['link_sub_type'])
            return_value['property'].add(file_properties['extra_values']['link_type'])
            return_value['property'].update(file_properties['extra_values'].get('property', []))
        elif filetype == 'relevance':
            for k in passed[filetype]:
                # simply dict value to top level
                return_value[k] = passed[filetype][k]
        elif filetype == 'refereed' and passed[filetype]:
            return_value['property'].add('REFEREED')
        elif value != file_properties['default_value'] or file_properties.get('copy_default', False):
            # otherwise, copy value
            return_value[filetype] = passed[filetype]

    if passed.get('pub_openaccess', False):
        return_value['property'].add('PUB_OPENACCESS')
    add_refereed_property(return_value)
    add_article_property(return_value, passed.get('nonarticle', False))
    return_value['property'] = sorted(return_value['property'])
    return_value['esource'] = sorted(return_value['esource'])
    add_data_summary(return_value)
    add_citation_count_norm_field(return_value, passed)
    
    # finally, delted the keys not in the nonbib protobuf
    not_needed = ['author', 'canonical', 'citation', 'download', 'nonarticle', 'ocrabstract', 'private', 'pub_openaccess',
                  'reads', 'refereed', 'relevance']
    for n in not_needed:
        return_value.pop(n, None)
    return return_value


def add_citation_count_norm_field(return_value, original):
    author_count = len(original.get('author', ()))
    return_value['citation_count_norm'] = return_value.get('citation_count', 0) / float(max(author_count, 1))


def add_refereed_property(return_value):
    if'REFEREED' not in return_value['property']:
        return_value['property'].add('NOT REFEREED')


def add_article_property(return_value, nonarticle):
    if nonarticle:
        return_value['property'].add('NONARTICLE')
    else:
        return_value['property'].add('ARTICLE')


def add_data_summary(return_value):
    """iterate over all data links to create data field

    "data": ["CDS:1", "NED:1953", "SIMBAD:1", "Vizier:1"]"""
    data_value = []
    total_link_counts = 0
    for r in return_value.get('data_links_rows', []):
        if r['link_type'] == 'DATA':
            v = r['link_sub_type'] + ':' + str(r.get('item_count', 0))
            data_value.append(v)
            total_link_counts += int(r.get('item_count', 0))
    return_value['data'] = sorted(data_value)
    return_value['total_link_counts'] = total_link_counts


def convert_data_link(filetype, value):
    """convert one data link row"""
    file_properties = data_files[filetype]
    d = {}
    d['link_type'] = file_properties['extra_values']['link_type']
    link_sub_type_suffix = ''
    if value is dict and 'subparts' in value and 'item_count' in value['subparts']:
        link_sub_type_suffix = ' ' + str(value['subparts']['item_count'])
    if value is True:
        d['link_sub_type'] = file_properties['extra_values']['link_sub_type'] + link_sub_type_suffix
    elif 'link_sub_type' in value:
        d['link_sub_type'] = value['link_sub_type'] + link_sub_type_suffix
    elif 'link_sub_type' in file_properties['extra_values']:
        d['link_sub_type'] = file_properties['extra_values']['link_sub_type'] + link_sub_type_suffix
    if type(value) is bool:
        d['url'] = ['']
    else:
        if type(value['url']) is str:
            d['url'] = [value['url']]
        else:
            d['url'] = value['url']
        if 'title' in value:
            d['title'] = value['title']
        if 'item_count' in value:
            d['item_count'] = value['item_count']
    return d


def read_next():
    """read all the info for the next bibcode into a dict"""
    global data_files
    d = {}
    for x in data_files:
        if x is 'canonical':
            d['canonical'] = data_files['canonical']['file_descriptor'].readline()
            if d['canonical'] is None:
                return None
            else:
                d['canonical'] = d['canonical'].strip()
        else:
            d.update(data_files[x]['file_descriptor'].read_value_for(d['canonical']))
    return d


def read_next_bibcode(bibcode):
    """read all the info for the passed bibcode into a dict"""
    d = {}
    d['canonical'] = bibcode
    for x in data_files:
        if x is not 'canonical':
            d.update(data_files[x]['file_descriptor'].read_value_for(bibcode))
    return d


def open_all(root_dir='/proj/ads/abstracts'):
    """simply open file descriptors to all the input files

    we store these descriptors in the file properties object"""

    for x in data_files:
        data_files[x]['file_descriptor'] = reader.StandardFileReader(x, root_dir + data_files[x]['path'])

        
def skip_lines(n):
    c = 0
    logger.info('starting to skip canonical lines')
    while c < n:
        data_files['canonical']['file_descriptor'].readline()
        if c % 1000 == 0:
            print('skipping canonical at {}'.format(c))
        c = c + 1
    logger.info('done skippline lines')


cache = {}

# def init_cache(root_dir=app.conf['INPUT_DATA_ROOT'])):
def init_cache(root_dir='/proj/ads/abstract/'):
    global cache
    if cache:
        # init has already been called
        return cache
    cache['reference'] = ReferenceNetwork(root_dir + data_files['reference']['path'])
    cache['citation'] = CitationNetwork(root_dir + data_files['citation']['path'])
    cache['refereed'] = Refereed(root_dir + data_files['reference']['path'])
    return cache


def get_cache():
    return cache


def compute_diffs():
    logger.info('compute diffs starting')
    diffs.sort_input_files()
    diffs.compute_changed_bibcodes()
    diffs.merge_changed_bibcodes()
    logger.info('compute diffs completed')
