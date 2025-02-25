
from datetime import datetime
from collections import defaultdict

from adsmsg import NonBibRecord, NonBibRecordList, MetricsRecord, MetricsRecordList
from adsdata import tasks, reader
from adsdata.memory_cache import Cache
from adsdata.file_defs import data_files, data_files_CC, computed_fields

class Processor:
    """use reader and cache to compute nonbib and metrics protobufs, send to master"""
    def __init__(self, compute_metrics=True, compute_CC = False):
        self.compute_metrics = compute_metrics
        self.compute_CC = compute_CC
        self.data_dict = None
        if self.compute_CC:
            self.data_dict = data_files_CC
        else:
            self.data_dict = data_files
        self.logger = tasks.app.logger
        self.readers = {}

    def __enter__(self):
        self._open_all()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._close_all()

    def process_bibcodes(self, bibcodes):
        """send nonbib and metrics records to master for the passed bibcodes
        for each bibcode
            read nonbib data from files, generate nonbib protobuf
            compute metrics, generate protobuf"""
        # batch up messages to master for improved performance
        nonbib_protos = NonBibRecordList()
        metrics_protos = MetricsRecordList()

        for bibcode in bibcodes:
            try:
                nonbib = self._read_next_bibcode(bibcode)
                converted = self._convert(nonbib)
                if not self.compute_CC:
                    nonbib_proto = NonBibRecord(**converted)
                    nonbib_protos.nonbib_records.extend([nonbib_proto._data])
                if self.compute_metrics:
                    met = self._compute_metrics(nonbib)
                    metrics_proto = MetricsRecord(**met)
                    metrics_protos.metrics_records.extend([metrics_proto._data])
            except Exception as e:
                self.logger.error('serious error in process.process_bibcodes for bibcode {}, error {}'.format(bibcode, e))
                self.logger.exception('general stacktrace')
        if not self.compute_CC: tasks.task_output_nonbib.delay(nonbib_protos)
        tasks.task_output_metrics.delay(metrics_protos)

    def _convert(self, passed):
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
            file_properties = self.data_dict[filetype] #data_files[filetype]
            if filetype == 'canonical':
                return_value['bibcode'] = passed['canonical']
            if (value is dict and dict and 'property' in value[filetype]):
                return_value['property'].update(value[filetype]['property'])
            if (type(file_properties['default_value']) is bool):
                return_value[filetype] = value[filetype]
                value = value[filetype]
            if ('extra_values' in file_properties and 'link_type' in file_properties['extra_values'] and value != file_properties['default_value']):
                # here with one or more real datalinks value(s)
                # add each data links dict to existing list of dicts
                # tweak some values (e.g., sub_link_type) in original dict
                if type(value) is bool or type(value) is dict:
                    d = self._convert_data_link(filetype, value)
                    return_value['data_links_rows'].append(d)
                elif type(value) is list:
                    for v in value:
                        d = self._convert_data_link(filetype, v)
                        return_value['data_links_rows'].append(d)
                else:
                    self.logger.error('serious error in process._convert with {} {} {}'.format(filetype, type(value), value))

                if file_properties['extra_values']['link_type'] == 'ESOURCE':
                    return_value['esource'].add(file_properties['extra_values']['link_sub_type'])
                return_value['property'].add(file_properties['extra_values']['link_type'])
                return_value['property'].update(file_properties['extra_values'].get('property', []))
            elif ('extra_values' in file_properties and value != file_properties['default_value']):
                if 'property' in file_properties['extra_values']:
                    return_value['property'].update(file_properties['extra_values']['property'])

            elif value != file_properties['default_value'] or file_properties.get('copy_default', False):
                # otherwise, copy value
                return_value[filetype] = passed[filetype]
            if filetype == 'relevance':
                for k in passed[filetype]:
                    # simply add all dict value to top level
                    return_value[k] = passed[filetype][k]

        self._add_refereed_property(return_value)
        self._add_article_property(return_value, passed)
        return_value['property'] = sorted(return_value['property'])
        return_value['esource'] = sorted(return_value['esource'])
        self._add_data_summary(return_value)
        return_value['data_links_rows'] = self._merge_data_links(return_value['data_links_rows'])
        self._add_citation_count_fields(return_value, passed)

        # time for computed fields
        for k, v in computed_fields.items():
            f = getattr(self, v['converter_function'], None)
            if f is None:
                self.logger.error('serious error in process._covert, expected converter_function {} for field {} not found'.format(v['converter_function'], k))
            else:
                x = f(return_value)
                return_value.update(x)

        # finally, delete the keys not in the nonbib protobuf
        not_needed = ['author', 'canonical', 'citation', 'deleted', 'deprecated_citation_count', 'doi', 'download', 'item_count', 'nonarticle',
                      'ocrabstract', 'preprint', 'private', 'pub_openaccess', 'pub2arxiv',
                      'reads', 'refereed', 'relevance', 'toc']
        for n in not_needed:
            return_value.pop(n, None)
        return return_value

    def _add_citation_count_fields(self, return_value, original):
        author_count = len(original.get('author', ()))
        citation_count = len(return_value.get('citation', ()))
        return_value['citation_count'] = citation_count
        return_value['citation_count_norm'] = citation_count / float(max(author_count, 1))

    def _add_refereed_property(self, return_value):
        if'REFEREED' not in return_value['property']:
            return_value['property'].add('NOT REFEREED')

    def _add_article_property(self, return_value, d):
        x = d.get('nonarticle', False)
        if type(x) is dict:
            x = x['nonarticle']
        if x:
            return_value['property'].add('NONARTICLE')
        else:
            return_value['property'].add('ARTICLE')

    def _add_data_summary(self, return_value):
        """iterate over all data links to create data field
        "data": ["CDS:2", "NED:1953", "SIMBAD:1", "Vizier:1"]"""
        total_link_counts = 0
        subtype_to_count = defaultdict(int)
        for r in return_value.get('data_links_rows', []):
            if r['link_type'] == 'DATA':
                c = int(r.get('item_count', 0))
                subtype_to_count[r['link_sub_type']] += c
                total_link_counts += c
        data_value = []
        for k in sorted(subtype_to_count.keys()):
            v = k + ':' + str(subtype_to_count[k])
            data_value.append(v)
        return_value['data'] = data_value
        return_value['total_link_counts'] = total_link_counts

    def _merge_data_links(self, datalinks):
        """data links with matching link_type and link_sub_type must be merged"""
        grouped = defaultdict(list)
        # Find duplicated type:subtype entries
        for d in datalinks:
            key = "{}:{}".format(d['link_type'], d['link_sub_type'])
            grouped[key].append(d)
        if len(grouped) == len(datalinks):
            # No duplicated entries found
            return datalinks
        else:
            new_datalinks = []
            for matches in grouped.values():
                if len(matches) == 1:
                    # Just one element of this kind, no need to merge
                    new_datalinks.append(matches[0])
                else:
                    # Merge matched elements into a single element
                    first = matches[0]
                    for m in matches[1:]:
                        first['url'].extend(m['url'])
                        first['title'].extend(m['title'])
                        first['item_count'] += m.get('item_count', 1)
                    new_datalinks.append(first)
            return new_datalinks

    # def _convert_data_link(self, filetype, value):
    #     """convert one data link row"""
    #     file_properties = self.data_dict[filetype] #data_files[filetype]
    #     d = {}
    #     d['link_type'] = file_properties['extra_values']['link_type']
    #     link_sub_type_suffix = ''
    #     if value is dict and 'subparts' in value and 'item_count' in value['subparts']:
    #         link_sub_type_suffix = ' ' + str(value['subparts']['item_count'])
    #     if value is True:
    #         d['link_sub_type'] = file_properties['extra_values']['link_sub_type'] + link_sub_type_suffix
    #     elif 'link_sub_type' in value:
    #         d['link_sub_type'] = value['link_sub_type'] + link_sub_type_suffix
    #     elif 'link_sub_type' in file_properties['extra_values']:
    #         d['link_sub_type'] = file_properties['extra_values']['link_sub_type'] + link_sub_type_suffix
    #     if type(value) is bool:
    #         d['url'] = ['']
    #         d['title'] = ['']
    #         d['item_count'] = 0
    #     elif type(value) is dict:
    #         d['url'] = value.get('url', [''])
    #         if type(d['url']) is str:
    #             d['url'] = [d['url']]
    #         d['title'] = value.get('title', [''])
    #         if type(d['title']) is str:
    #             d['title'] = [d['title']]
    #         # if d['title'] == ['']:
    #         #    d.pop('title')  # to match old pipeline
    #         d['item_count'] = value.get('item_count', 0)
    #     else:
    #         self.logger.error('serious error in process.convert_data_link: unexpected type for value, filetype = {}, value = {}, type of value = {}'.format(filetype, value, type(value)))
    #     breakpoint() # {'link_type': 'ESOURCE', 'link_sub_type': 'ADS_PDF', 'url': ['http://articles.adsabs.harvard.edu/pdf/2003ASPC..295..361M'], 'title': [''], 'item_count': 0}
    #     return d

    def _convert_data_link(self, filetype, value):
        """convert one data link row"""
        
        file_properties = self.data_dict[filetype]

        link_type = file_properties['extra_values']['link_type']
        link_sub_type = file_properties['extra_values'].get('link_sub_type', '')
        link_sub_type_suffix = ''

        if isinstance(value, dict) and 'subparts' in value:
            link_sub_type_suffix = f" {value['subparts'].get('item_count', '')}".strip()
        
        # Determine the link sub type
        if not link_sub_type and isinstance(value, dict) and 'link_sub_type' in value:
            link_sub_type = value['link_sub_type']
        
        link_sub_type += link_sub_type_suffix
        
        # Initialize result dictionary
        link_data =  { 'link_type': link_type, 
                        'link_sub_type': link_sub_type,
                        "url": [""],
                        "title": [""],
                        "item_count": 0
                    }
                

        if isinstance(value, dict):
            link_data['url'] = value.get('url', [''])
            link_data['title'] = value.get('title', [''])
            link_data['item_count'] = value.get('item_count', 0)
            
            if isinstance(link_data['url'], str):
                link_data['url'] = [link_data['url']]
            if isinstance(link_data['title'], str):
                link_data['title'] = [link_data['title']]
        
        elif not isinstance(value, bool):
            self.logger.error(
                f"Serious error in process.convert_data_link: unexpected type for value, filetype = {filetype}, "
                f"value = {value}, type of value = {type(value)}"
            )
        return link_data

    def _read_next_bibcode(self, bibcode):
        """read all the info for the passed bibcode into a dict"""
        d = {}
        d['canonical'] = bibcode
        for x in self.data_dict.keys(): #data_files.keys():
            if x != 'canonical':
                v = self.readers[x].read_value_for(bibcode)
                d.update(v)
        return d

    def _open_all(self):
        """open all input files"""
        self.readers = {}
        for x in self.data_dict.keys(): #data_files.keys():
            self.readers[x] = reader.NonbibFileReader(x, self.data_dict[x]) #data_files[x])

    def _close_all(self):
        for x in self.data_dict.keys(): #data_files.keys():
            if x in self.readers:
                self.readers[x].close()
                self.readers.pop(x)

    def _compute_metrics(self, d):
        """compute metrics dict based on the passed dict with the full nonbib record read and the cache"""
        bibcode = d['canonical']
        author_num = 1
        if 'author' in d and d['author']:
            author_num = max(len(d['author']), 1)

        refereed = Cache.get('refereed')
        bibcode_to_references = Cache.get('reference')
        bibcode_to_cites = Cache.get('citation')

        citations = bibcode_to_cites[bibcode]
        citations_json_records = []
        citation_normalized_references = 0.0
        citation_num = 0
        if citations:
            citation_num = len(citations)
        refereed_citations = []
        reference_num = len(bibcode_to_references[bibcode])
        total_normalized_citations = 0.0

        if citation_num:
            for citation_bibcode in citations:
                citation_refereed = citation_bibcode in refereed
                len_citation_reference = len(bibcode_to_references[citation_bibcode])
                citation_normalized_references = 1.0 / float(max(5, len_citation_reference))
                total_normalized_citations += citation_normalized_references
                tmp_json = {"bibcode":  citation_bibcode,
                            "ref_norm": citation_normalized_references,
                            "auth_norm": 1.0 / author_num,
                            "pubyear": int(bibcode[:4]),
                            "cityear": int(citation_bibcode[:4])}
                citations_json_records.append(tmp_json)
                if (citation_refereed):
                    refereed_citations.append(citation_bibcode)

        refereed_citation_num = len(refereed_citations)

        # annual citations
        today = datetime.today()
        resource_age = max(1.0, today.year - int(bibcode[:4]) + 1)
        an_citations = float(citation_num) / float(resource_age)
        an_refereed_citations = float(refereed_citation_num) / float(resource_age)

        # normalized info
        rn_citations = total_normalized_citations
        modtime = datetime.now()
        reads = d['reads']
        downloads = d['download']
        return_value = {'bibcode': bibcode,
                        'an_citations': an_citations,
                        'an_refereed_citations': an_refereed_citations,
                        'author_num': author_num,
                        'citation_num': citation_num,
                        'citations': citations,
                        'downloads': downloads,
                        'modtime': modtime,
                        'reads': reads,
                        'refereed': bibcode in refereed,
                        'refereed_citations': refereed_citations,
                        'refereed_citation_num': refereed_citation_num,
                        'reference_num': reference_num,
                        'rn_citations': rn_citations,
                        'rn_citation_data': citations_json_records}
        return return_value

    def _compute_bibgroup_facet(self, d):
        bibgroup = d.get('bibgroup', None)
        if bibgroup is None:
            return {}
        bibgroup_facet = sorted(list(set(bibgroup)))
        return {'bibgroup_facet': bibgroup_facet}
