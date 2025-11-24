from adsdata import tasks
from adsputils import load_config

class NonbibFileReader(object):
    """reads nonbib column files
    file reading/parsing is controlled by the file's properties dict in file_defs
    every line must start with a bibcode
    file must be sorted by bibcode
    """
    bibcode_length = 19
    config = load_config()

    def __init__(self, filetype, file_info):
        """passed file type (e.g., canonical) and relevant part of file_defs"""
        self.filetype = filetype
        self.file_info = file_info
        self.filename = self.config.get('INPUT_DATA_ROOT', './') + file_info['path']
        self.logger = tasks.app.logger
        self.read_count = 0   # used in logging
        self.buffer = None  # holds at most one line of text
        self._iostream = open(self.filename, 'r', encoding='utf-8')

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()
    
    def __iter__(self):
        return self
    
    def next(self):
        return self._iostream.next()
    
    def close(self):
        self._iostream.close()
        del self._iostream

    def _pushline(self, s):
        """the buffer is used when we read a line that is beyond the desired bibcode
           and we need to unread it"""
        if self.buffer:
            self.logger.error('error in file {}, {}, _pushline called when buffer was not empty.  File line number: read line: {}, buffer: {}'.format(self.filetype, self.filename, self.read_count, s, self.buffer))
        self.buffer = s

    def _readline(self):
        """return the next valid line or empty string at eof 
           used to read all files"""
        if self.buffer:
            line = self.buffer
            self.buffer = None
            return line
        if self._iostream.closed:
            return ''
        self.read_count += 1
        line = self._iostream.readline()
        while len(line) > 0 and len(line) < self.bibcode_length:
            self.logger.error('error, invalid short line in readline {} filename: {} at line {}, line length less then length of bibcode, line: {}'.format(self.filetype, self.filename, self.read_count, line))
            self.read_count += 1
            line = self._iostream.readline()
        return line
    
    def read_value_for(self, bibcode):
        """return the value from the file for the passed bibcode
        returns default value if bibcode is not in file

        return value is a dict with the key of self.filetype

        some files repeat a bibcode on consecutive lines to provide multiple values
        other files do not repeat a bibcode and provide multiple values on a single line
        other files (e.g., relevance/docmetrics.tab) have multiple values
        some files have associated effects on values like property field
        this reader handles all cases based on the file property dict
        """
        # first, are we at eof?
        current_line = self._readline()
        if len(current_line) == 0:
            # here if we are already at eof, bibcode isn't in file
            return self._convert_value(self.file_info['default_value'])

        # next, skip over lines in file until we:
        #   either find the passed bibcode or determine it isn't in the file
        skip_count = 0
        # If you are wondering why this works: while the index files in the Classic
        # Back Office are sorted case INsensitively, their sorting is converted to
        # case sensitive when local copies are created in the pipeline container
        # (see the script "copy_input_files.sh" located in the "root/app/bin" directory
        # of the image for backoffice-data-pipeline in BeeHive).   
        while len(current_line) != 0 and self._get_bibcode(current_line) < bibcode:
            current_line = self._readline()
            skip_count = skip_count + 1

        # at this point, we have either read to the desired bibcode
        # or it doesn't exist and we read past it
        if len(current_line) == 0 or bibcode != self._get_bibcode(current_line):
            # bibcode not in file
            self._pushline(current_line)
            return self._convert_value(self.file_info['default_value'])

        if isinstance(self.file_info['default_value'], bool):
            return self._convert_value(True)  # boolean files only hold bibcodes, all values are True
        # at this point, we have the first line with the bibcode in it
        # roll up possible other values on adjacent lines in file
        value = []
        if 'gpn/' in self.file_info['path'] or 'uat/' in self.file_info['path']:
            value.append("/".join(self._get_rest(current_line).split("\t")))
        elif 'mention/' in self.file_info['path'] or 'credit/' in self.file_info['path']:
            value.append(self._get_rest(current_line).split("\t")[0])
        else:
            value.append(self._get_rest(current_line))
        current_line = self._readline()
        while self.file_info.get('multiline', False) and (current_line not in [None, '']) and (bibcode == self._get_bibcode(current_line)):
            if 'gpn/' in self.file_info['path'] or 'uat/' in self.file_info['path']:
                value.append("/".join(self._get_rest(current_line).split("\t")))
            elif 'mention/' in self.file_info['path'] or 'credit/' in self.file_info['path']:
                value.append(self._get_rest(current_line).split("\t")[0])
            else:
                value.append(self._get_rest(current_line))
            current_line = self._readline()
            
        # at this point we have read beyond the desired bibcode, must back up
        self._pushline(current_line)
        # finally, convert raw input into something useful
        return self._convert_value(value)
        
    def _convert_value(self, value):
        """convert file string line to something more useful
        return a dict with filetype as key and value converted
        """
        if isinstance(value, str) and '\x00' in value:
            # there should not be nulls in strings
            self.logger.error('error string contained a null in file {} {}, line number: {}, value: {}'.format(self.filetype, self.filename, self.read_count, value))
            value = value.replace('\x00', '')

        return_value = value
        if isinstance(value, bool):
            d = {self.filetype: return_value}
            if 'extra_values' in self.file_info and value != self.file_info['default_value']:
                d.update(self.file_info['extra_values'])
            return {self.filetype: d}
        elif (len(value) > 0 and '\t' in value[0] and not self.file_info.get('tab_separated_pair', False)):
            # tab separator in string means we need to convert elements to array
            z = []
            for r in value:
                x = r.split('\t')
                if self.file_info.get('string_to_number', True):
                    # convert valid ints and floats to numeric representation
                    t = []
                    for y in x:
                        t.append(self._convert_scalar(y))
                    z.append(t)
            return_value = z
            if len(return_value) == 1:
                return_value = return_value[0]
        elif 'interleave' in self.file_info and value != self.file_info['default_value']:
            # here on multi-line dict (e.g., associations)
            # interleave data on successive lines e.g., merge first element in each array, second element, etc.
            #   since they also have subparts, these arrays will then put in dict with the cooresponding key
            x = {}
            for k in self.file_info['subparts']:
                x[k] = []
            for r in value:
                # For instance, in associations 'r' should contain:
                #   URL title
                # where title may contain spaces too
                parts = r.split(' ', 1)  # parts will contain [URL, title]
                if len(parts) < len(self.file_info['subparts']):
                    self.logger.error('error in reader with interleave for {} file {}, incomplete value in line.  value = {}, parts = {} at line'.format(self.filetype, self.filename, value, parts, self.read_count))
                else:
                    for i, k in enumerate(self.file_info['subparts']):
                        v = parts[i].strip()
                        x[k].append(v)
            return_value = x
        elif (self.file_info.get('tab_separated_pair', False)):
            # files like simbad_objects, ned_objects have tabs separating an id and 0 or more types
            x = []
            for a in value:
                t = a.replace('\t', ' ')
                if ' ' not in t:
                    # when no type is present we need a trailing space
                    t += ' '
                x.append(t)
            return_value = x
        elif (len(value) > 1):
            x = []
            for r in value:
                x.append(r.replace('\t', ' ').strip())
            return_value = x
        # convert array to dict if needed
        if 'subparts' in self.file_info and return_value != self.file_info['default_value'] and 'interleave' not in self.file_info:
            if type(return_value[0]) is list:
                x = []
                for r in return_value:
                    x.append(self._convert_subparts(r))
            else:
                x = self._convert_subparts(return_value)
            return_value = x

        # are there extra_values to add to dict
        if 'extra_values' in self.file_info:
            self._add_extra_values(return_value)
        return {self.filetype: return_value}

    def _add_extra_values(self, current):
        if current != self.file_info['default_value'] and type(current) is dict:
            current.update(self.file_info['extra_values'])
        elif current != self.file_info['default_value'] and type(current) is list:
            # here with array of dicts, put extra_values in each dict
            for x in current:
                v = self.file_info['extra_values']
                if type(v) is dict and type(x) is dict:
                    x.update(v)
                else:
                    self.logger.error('serious error in reader._add_extra_values, non dict value, extra_values = {}, processing element = {},  passed current = {}'.format(x, v, current))

    def _convert_subparts(self, current):
        d = {}
        for i, k in enumerate(self.file_info['subparts']):
            v = ''
            if i < len(current):
                v = current[i]
            if type(k) is list:
                # here if key is in a list by itself which means values should be in a list
                k = k[0]
                v = [v]
            d[k] = v
        return d

    def _get_bibcode(self, s):
        """return the  bibcode from the from of the line"""
        if s is None:
            return None
        if len(s) < self.bibcode_length:
            self.logger.error('error, invalid short line in file {} {} at line {}, line length of {} is less then length of bibcode, line = {}'.format(self.filetype, self.filename, self.read_count, len(s), s))
            return s
        return s[:self.bibcode_length].strip()

    def _get_rest(self, s):
        """return the text after the bibcode and first tab separator"""
        if len(s) < self.bibcode_length + 1:
            self.logger.error('error, in _get_rest with invalid short line in file {} {} at line {}, line length less then length of bibcode plus 1, line = {}'.format(self.filetype, self.filename, self.read_count, s))
            return ''
        return s[self.bibcode_length + 1:].strip()
                                 
    def _convert_scalar(self, s):
        if s.isdigit():
            return int(s)
        try:
            x = float(s)
            return x
        except ValueError:
            return s.strip()

