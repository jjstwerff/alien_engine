"""Tables inside the database"""
import os
import unittest
import subprocess

from fields import String, Number, Enum, Set, Record, Store
from rbtree import RBDict
from read import scan_file, reading
from server import Server


class Step(Record):
    """Period for the automatic invoicing"""
    __slots__ = 'step', 'type', 'url', 'data', 'response', 'changes'
    path = 'periods'
    fields = [
        Number('step'),
        Enum('type', ['data', 'call']),
        String('url'),
        String('data'),
        String('response'),
        String('changes')]
    keys = ['step']

    def __init__(self, parent):
        self.parent = parent
        self.step = len(parent.steps) + 1
        self.type = 1
        self.url = ''
        self.data = ''
        self.response = None
        self.changes = None

    def store(self):
        """Store the Step"""
        self.parent.steps[self.get_id()] = self

    def remove(self):
        """Remove the Step from the test"""
        del self.parent.steps[self.get_id()]

    def removable(self, general):
        """This record can be removed savely"""
        return None

    def show(self):
        """String to show the record with"""
        return self.fields[1].show(self.type) + ' ' + self.url

    def find(self, data):
        """Find the record with the relation key"""
        if data['step'] not in self.root().steps:
            return None
        return self.root().steps[data['start']]


class TestFile(Record):
    """General record that holds the steps of a test"""
    __slots__ = 'description', 'steps'
    path = ''
    fields = [
        String('description'),
        Set('steps', Step)]

    def __init__(self):
        self.description = ''
        self.steps = RBDict()

    def store(self):
        """This this the top level element"""
        pass

    def remove(self):
        """The top level element cannot be removed"""
        pass

    def removable(self, general):
        """This record cannot be removed savely"""
        return {"testFile": None}


def init(store):
    """Add some fields that are forward definitions"""
    testfile = TestFile()
    store.init(testfile)
    store.register(Step)
    return testfile


def perform(testfile, result):
    """Perform the steps of a test"""
    general = None
    server = None
    result.description = testfile.description
    for step in testfile.steps:
        if step.type == 1:  # data
            general = reading(step.data)
            server = Server(general, None, None)
            rstep = Step(result)
            rstep.type = 1
            rstep.url = step.url
            rstep.data = str(general)
            rstep.store()
            general.stored.changes()
        elif step.type == 2:  # call
            res = server.call(step.url, step.data)
            rstep = Step(result)
            rstep.type = 2
            rstep.url = step.url
            rstep.data = step.data
            rstep.response = res
            rstep.changes = general.changes()
            rstep.store()


def scanning(subdir, file, res_file):
    """Scan a file for test steps and fill the result file"""
    store = Store()
    res_store = Store()
    testfile = init(store)
    result = init(res_store)
    scan_file(os.path.join(subdir, file), testfile)
    perform(testfile, result)
    fd = open(os.path.join(subdir, res_file), "w")
    fd.write(str(result))
    fd.close()
    return os.system(
        '/usr/bin/cmp -s ' + os.path.join(subdir, file) + ' ' +
        os.path.join(subdir, res_file))


class TestImport(unittest.TestCase):
    """Scan the test directory for .test files"""
    def do_tests(self):
        """Perform all the tests inside the given directory"""
        path = "test"
        first = None
        problems = 0
        for subdir, _, files in os.walk(path):
            for file in files:
                if not file.endswith(".test"):
                    continue
                res_file = file[:-4] + 'result'
                if scanning(subdir, file, res_file):
                    if problems == 0:
                        first = (subdir, file, res_file)
                    problems += 1
                else:
                    os.unlink(os.path.join(subdir, res_file))
        if problems > 0:
            subprocess.Popen([
                '/usr/bin/meld',
                os.path.join(first[0], first[1]),
                os.path.join(first[0], first[2])
            ])
        self.assertEqual(0, problems)
