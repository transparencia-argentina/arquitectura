# Python bindings to control Google Refine from the command line

# Originally written by David Huynh (@dfhuynh)

# requires installation of urllib2_file from https://github.com/seisen/urllib2_file/#readme
import urllib2_file
import urllib2, urlparse, os.path, time, json


class Refine:
    def __init__(self, server='http://127.0.0.1:3333'):
        self.server = server[0, -1] if server.endswith('/') else server

    def new_project(self, project_file=None, project_url=None, options=None):
        data = {}

        if project_file:
            file_name = os.path.split(project_file)[-1]
            data['project-file'] = {
                'fd': open(project_file),
                'filename': file_name
            }
        if project_url:
            file_name = os.path.split(urlparse.urlparse(project_url).path)[-1]
            data['project-url'] = project_url
        if project_file and project_url:
            raise Exception("Only project_file or project_url valid, not both")

        project_name = options['project_name'] if options != None and 'project_name' in options else file_name
        data['project-name'] = project_name

        response = urllib2.urlopen(self.server + '/command/core/create-project-from-upload', data)
        response_body = response.read()
        url_params = urlparse.parse_qs(urlparse.urlparse(response.geturl()).query)
        if 'project' in url_params:
            id = url_params['project'][0]
            return RefineProject(self.server, id, project_name)

        # TODO: better error reporting
        return None


class RefineProject:
    def __init__(self, server, id, project_name):
        self.server = server
        self.id = id
        self.project_name = project_name

    def wait_until_idle(self, polling_delay=0.5):
        while True:
            response = urllib2.urlopen(self.server + '/command/core/get-processes?project=' + self.id)
            response_json = json.loads(response.read())
            if 'processes' in response_json and len(response_json['processes']) > 0:
                time.sleep(polling_delay)
            else:
                return

    def apply_operations(self, file_path, wait=True):
        fd = open(file_path)
        operations_json = fd.read()

        data = {
            'operations': operations_json
        }
        response = urllib2.urlopen(self.server + '/command/core/apply-operations?project=' + self.id, data)
        response_json = json.loads(response.read())
        if response_json['code'] == 'error':
            raise Exception(response_json['message'])
        elif response_json['code'] == 'pending':
            if wait:
                self.wait_until_idle()
                return 'ok'

        return response_json['code']  # can be 'ok' or 'pending'

    def export_rows(self, format='tsv', printColumnHeader=True):
        data = {
            'engine': '{"facets":[],"mode":"row-based"}',
            'project': self.id,
            'format': format,
            'printColumnHeader': printColumnHeader
        }
        response = urllib2.urlopen(self.server + '/command/core/export-rows/' + self.project_name + '.' + format, data)
        return response.read()

    def delete_project(self):
        data = {
            'project': self.id
        }
        response = urllib2.urlopen(self.server + '/command/core/delete-project', data)
        response_json = json.loads(response.read())
        return 'code' in response_json and response_json['code'] == 'ok'
