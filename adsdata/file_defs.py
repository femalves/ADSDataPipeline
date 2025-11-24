
from collections import OrderedDict
from adsputils import load_config
config = load_config()
# file properties definitions
# use dict to hold each input files and their properties and idiosycrasies

data_files = OrderedDict()
data_files['mention'] = {'path': 'links/mention/all.links', 'default_value': [], 'multiline': True}
data_files['credit'] = {'path': 'links/credit/all.links', 'default_value': [], 'multiline': True}
data_files['canonical'] = {'path': 'bibcodes.list.can', 'default_value': ''}
data_files['author'] = {'path': 'links/facet_authors/all.links', 'default_value': []}
data_files['bibgroup'] = {'path': 'links/bibgroups/all.links', 'default_value': [], 'multiline': True}
data_files['citation'] = {'path': 'links/citation/all.links', 'default_value': [], 'multiline': True}
data_files['download'] = {'path': 'links/reads/downloads.links', 'default_value': []}
data_files['grants'] = {'path': 'links/grants/all.links', 'default_value': [], 'string_to_number': False, 'multiline': True, 'tab_separated_pair': True}
data_files['ned_objects'] = {'path': 'links/ned/ned_objects.tab', 'default_value': [], 'string_to_number': False, 'multiline': True, 'tab_separated_pair': True}
data_files['nonarticle'] = {'path': 'links/nonarticle/all.links', 'default_value': False, 'multiline': True}
data_files['ocrabstract'] = {'path': 'links/ocr/all.links', 'default_value': False,
                             'extra_values': {'property': ['OCRABSTRACT']}}
data_files['private'] = {'path': 'links/private/all.links', 'default_value': False,
                         'extra_values': {'property': ['PRIVATE']}}
data_files['pub_openaccess'] = {'path': 'links/openaccess/pub.dat', 'default_value': False,
                                'extra_values': {'property': ['PUB_OPENACCESS', 'OPENACCESS']}}
data_files['readers'] = {'path': 'links/alsoread_bib/all.links', 'default_value': [], 'multiline': True}
data_files['reads'] = {'path': 'links/reads/all.links', 'default_value': []}
data_files['refereed'] = {'path': 'links/refereed/all.links', 'default_value': False, 'extra_values': {'property': ['REFEREED']}}
data_files['reference'] = {'path': 'links/reference/all.links', 'default_value': [], 'multiline': True}
data_files['relevance'] = {'path': 'links/relevance/docmetrics.tab', 'default_value': {},
                           'subparts': ['boost', 'deprecated_citation_count', 'read_count', 'norm_cites']}
data_files['simbad_objects'] = {'path': 'links/simbad/simbad_objects.tab', 'default_value': [],
                                'string_to_number': False, 'multiline': True, 'tab_separated_pair': True}
data_files['pub_html'] = {'path': 'links/electr/all.links', 'default_value': {},
                          'extra_values': {'link_type': 'ESOURCE', 'link_sub_type': 'PUB_HTML'},
                          'subparts': [['url']]}
data_files['eprint_html'] = {'path': 'links/eprint_html/all.links', 'default_value': {},
                             'extra_values': {'link_type': 'ESOURCE', 'link_sub_type': 'EPRINT_HTML', 'property': ['EPRINT_OPENACCESS', 'OPENACCESS']},
                             'subparts': ['url']}
data_files['pub_pdf'] = {'path': 'links/pub_pdf/all.links', 'default_value': {},
                         'extra_values': {'link_type': 'ESOURCE', 'link_sub_type': 'PUB_PDF'},
                         'subparts': ['url']}
data_files['ads_pdf'] = {'path': 'links/ads_pdf/all.links', 'default_value': {},
                         'extra_values': {'link_type': 'ESOURCE', 'link_sub_type': 'ADS_PDF', 'property': ['ADS_OPENACCESS', 'OPENACCESS']},
                         'subparts': [['url']]}
data_files['eprint_pdf'] = {'path': 'links/eprint_pdf/all.links', 'default_value': {},
                            'extra_values': {'link_type': 'ESOURCE', 'link_sub_type': 'EPRINT_PDF', 'property': ['EPRINT_OPENACCESS', 'OPENACCESS']},
                            'subparts': ['url']}
data_files['author_html'] = {'path': 'links/author_html/all.links', 'default_value': {},
                             'extra_values': {'link_type': 'ESOURCE', 'link_sub_type': 'AUTHOR_HTML', 'property': ['AUTHOR_OPENACCESS', 'OPENACCESS']},
                             'subparts': ['url']}
data_files['author_pdf'] = {'path': 'links/author_pdf/all.links', 'default_value': {},
                            'extra_values': {'link_type': 'ESOURCE', 'link_sub_type': 'AUTHOR_PDF', 'property': ['AUTHOR_OPENACCESS', 'OPENACCESS']},
                            'subparts': ['url']}
data_files['pmc_html'] = {'path': 'links/pmc_html/PMC.dat', 'default_value': {},
                             'extra_values': {'link_type': 'ESOURCE', 'link_sub_type': 'PMC_HTML', 'property': ['PMC_OPENACCESS', 'OPENACCESS']},
                             'subparts': ['url']}
data_files['pmc_pdf'] = {'path': 'links/pmc_pdf/PMC.dat', 'default_value': {},
                            'extra_values': {'link_type': 'ESOURCE', 'link_sub_type': 'PMC_PDF', 'property': ['PMC_OPENACCESS', 'OPENACCESS']},
                            'subparts': ['url']}
data_files['ads_scan'] = {'path': 'links/ads_scan/all.links', 'default_value': {},
                          'extra_values': {'link_type': 'ESOURCE', 'link_sub_type': 'ADS_SCAN', 'property': ['ADS_OPENACCESS', 'OPENACCESS']},
                          'subparts': [['url']]}
data_files['associated'] = {'path': 'links/associated/all.links', 'default_value': {},
                            'extra_values': {'link_type': 'ASSOCIATED', 'link_sub_type': 'NA'},
                            'subparts': ['url', 'title'], 'multiline': True, 'interleave': True}
data_files['presentation'] = {'path': 'links/video/all.links', 'default_value': {},
                              'extra_values': {'link_type': 'PRESENTATION', 'link_sub_type': 'NA'},
                              'subparts': [['url']], 'multiline': True}
data_files['librarycatalog'] = {'path': 'links/library/all.links', 'default_value': {},
                                'extra_values': {'link_type': 'LIBRARYCATALOG', 'link_sub_type': 'NA'},
                                'subparts': [['url']], 'multiline': True}
data_files['inspire'] = {'path': 'links/spires/all.links', 'default_value': {},
                         'extra_values': {'link_type': 'INSPIRE', 'link_sub_type': 'NA'},
                         'subparts': [['url']], 'multiline': True}
data_files['toc'] = {'path': 'links/toc/all.links', 'default_value': False,
                     'extra_values': {'link_type': 'TOC', 'link_sub_type': 'NA'}}
data_files['data_link'] = {'path': 'links/facet_datasources/datasources.links', 'default_value': {},
                           'extra_values': {'link_type': 'DATA', 'property': ['DATA']}, 'multiline': True,
                           'subparts': ['link_sub_type', 'item_count', ['url'], ['title']]}
data_files['planetary_feature'] = {'path': 'links/gpn/all.links', 'default_value': [], 'multiline': True}

env_name = config.get('ENVIRONMENT', 'back-dev')
data_files['uat'] = {'path': 'links/uat/uat.list.'+str(env_name), 'default_value': [], 'multiline': True}

# file properties definitions required to generate metrics for CitationCapture records
# use dict to hold each input files and their properties and idiosycrasies
data_files_CC = OrderedDict()
data_files_CC['canonical'] = {'path': 'bibcodes_CC.list.can.'+str(env_name), 'default_value': ''}
data_files_CC['author'] = {'path': 'links/facet_authors/facet_authors_CC.list.'+str(env_name), 'default_value': []}
data_files_CC['citation'] = {'path': 'links/citation/citations_CC.list.'+str(env_name), 'default_value': [], 'multiline': True}
data_files_CC['reference'] = {'path': 'links/reference/references_CC.list.'+str(env_name), 'default_value': [], 'multiline': True}

data_files_CC['download'] = {'path': 'links/reads/downloads.links', 'default_value': []}
data_files_CC['reads'] = {'path': 'links/reads/all.links', 'default_value': []}


# file properties for the merged files required to handle both Classic and CitationCapture records.
network_files = OrderedDict()
network_files['citation'] = {'path': 'links/citation/all.links.merged', 'default_value': [], 'multiline': True}
network_files['reference'] = {'path': 'links/reference/all.links.merged', 'default_value': [], 'multiline': True}
network_files['refereed'] = {'path': 'links/refereed/all.links', 'default_value': False, 'extra_values': {'property': ['REFEREED']}}

# computed fields are based on data read from the above files
# each function name is a member function in process and takes the entire nonbib dict as an argument
computed_fields = OrderedDict()
computed_fields['bibgroup_facet'] = {'converter_function': '_compute_bibgroup_facet'}



