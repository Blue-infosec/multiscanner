from __future__ import division, absolute_import, print_function, unicode_literals
import mock
import os
import sys

import multiscanner
from multiscanner.common import utils

# Makes sure we use the multiscanner in ../
CWD = os.path.dirname(os.path.abspath(__file__))

TEST_CONFIG_FILEPATH = '.tmpfile.ini'
TEST_REPORT = 'tmp_report.json'
TEST_FILES = os.path.join(CWD, 'files')


class _runmulti_tests(object):
    @classmethod
    def setup_class(cls):
        cls.real_mod_dir = multiscanner.config.MODULES_DIR
        cls.real_mod_list = multiscanner.config.MODULE_LIST
        multiscanner.config.MODULES_DIR = os.path.join(CWD, "modules")
        multiscanner.config.MODULE_LIST = multiscanner.config.get_modules()
        cls.filelist = utils.parse_dir(TEST_FILES)

    @classmethod
    def teardown_class(cls):
        multiscanner.config.MODULES_DIR = cls.real_mod_dir
        multiscanner.config.MODULE_LIST = cls.real_mod_list


class TestMultiscan(_runmulti_tests):
    def setup(self):
        multiscanner.config_init(TEST_CONFIG_FILEPATH, multiscanner._get_main_modules())
        multiscanner.update_ms_config_file(TEST_CONFIG_FILEPATH)
        self.result = multiscanner.multiscan(self.filelist)
        self.report = multiscanner.parse_reports(self.result, includeMetadata=False, python=True)
        self.report_m = multiscanner.parse_reports(self.result, includeMetadata=True, python=True)

    def teardown(self):
        os.remove(TEST_CONFIG_FILEPATH)

    def test_multiscan_results(self):
        for f in self.filelist:
            assert f in self.report
            assert f in self.report_m['Files']


class TestMain(_runmulti_tests):
    def setup(self):
        multiscanner.config_init(TEST_CONFIG_FILEPATH, multiscanner._get_main_modules())
        multiscanner.update_ms_config_file(TEST_CONFIG_FILEPATH)

    def teardown(self):
        try:
            os.remove(TEST_CONFIG_FILEPATH)
            os.remove(TEST_REPORT)
        except Exception as e:
            # TODO: log exception
            pass

    def test_basic_main(self):
        with mock.patch.object(sys, 'argv', ['ms.py', '-j', TEST_REPORT] + self.filelist):
            try:
                multiscanner._main()
            except SystemExit:
                pass


@mock.patch.object(multiscanner.config, 'CONFIG_FILEPATH', TEST_CONFIG_FILEPATH)
class TestInitNoConfig(_runmulti_tests):
    def test_basic_main(self):
        with mock.patch.object(sys, 'argv', ['ms.py', 'init']), \
                mock.patch('multiscanner.ms.input', return_value='y'):
            try:
                multiscanner._main()
            except SystemExit:
                pass

        with mock.patch.object(sys, 'argv', ['ms.py', '-j', TEST_REPORT] + self.filelist):
            try:
                multiscanner._main()
            except SystemExit:
                pass

    def teardown(self):
        try:
            os.remove(TEST_CONFIG_FILEPATH)
            os.remove(TEST_REPORT)
        except Exception as e:
            # TODO: log exception
            pass


class TestMissingConfig(_runmulti_tests):
    def setup(self):
        with mock.patch.object(sys, 'argv', ['ms.py', '-c', TEST_CONFIG_FILEPATH, 'init']), \
                mock.patch('multiscanner.ms.input', return_value='y'):
            try:
                multiscanner._main()
            except SystemExit:
                pass

    def test_config_init(self):
        config_object = multiscanner.MSConfigParser()
        config_object.read(TEST_CONFIG_FILEPATH)

        assert config_object.has_section('main')
        assert config_object.has_section('test_1')
        assert not config_object.has_section('Cuckoo')

    def test_fill_in_missing_config_sections(self):
        # Simulate a section missing from config file before multiscanner is imported/run
        config_object = multiscanner.MSConfigParser()
        config_object.read(TEST_CONFIG_FILEPATH)
        config_object.remove_section('main')
        config_object.remove_section('test_1')
        with open(TEST_CONFIG_FILEPATH, 'w') as conf_file:
            config_object.write(conf_file)
        multiscanner.update_ms_config_file(TEST_CONFIG_FILEPATH)

        # Run MultiScanner
        with mock.patch.object(sys, 'argv', ['ms.py', '-c', TEST_CONFIG_FILEPATH, TEST_FILES]):
            multiscanner._main()
        with open(TEST_CONFIG_FILEPATH, 'r') as conf_file:
            conf = conf_file.read()
            assert 'test_1' in conf

    def test_read_config_with_default(self):
        multiscanner.config.read_config(TEST_CONFIG_FILEPATH, {'test': {'foo': 'bar'}})
        with open(TEST_CONFIG_FILEPATH, 'r') as conf_file:
            conf = conf_file.read()
            assert 'foo' in conf

    def test_overwriting_config_on_reset(self):
        # Change a config val from default
        config_object = multiscanner.MSConfigParser()
        config_object.read(TEST_CONFIG_FILEPATH)
        config_object.set('test_2', 'ENABLED', 'False')
        with open(TEST_CONFIG_FILEPATH, 'w') as conf_file:
            config_object.write(conf_file)

        # Trigger reset_config and it gets overwritten
        self.setup()
        with mock.patch.object(sys, 'argv', ['ms.py', '-c', TEST_CONFIG_FILEPATH, '-j', TEST_REPORT, self.filelist[0]]):
            try:
                multiscanner._main()
            except SystemExit:
                pass

        with open(TEST_REPORT, 'r') as report_file:
            report = report_file.read()
        assert 'test_2' in report

        # teardown
        os.remove(TEST_REPORT)

    def test_config_init_no_overwrite(self):
        # Remove a section from config file
        config_object = multiscanner.MSConfigParser()
        config_object.read(TEST_CONFIG_FILEPATH)
        config_object.remove_section('test_1')
        with open(TEST_CONFIG_FILEPATH, 'w') as conf_file:
            config_object.write(conf_file)

        # this time we answer 'no' so config won't be overwritten, but missing modules' configs will be regenerated
        with mock.patch.object(sys, 'argv', ['ms.py', '-c', TEST_CONFIG_FILEPATH, 'init']), \
                mock.patch('multiscanner.ms.input', return_value='n'):
            try:
                multiscanner._main()
            except SystemExit:
                pass

        with open(TEST_CONFIG_FILEPATH, 'r') as conf_file:
            conf = conf_file.read()
            assert 'test_1' in conf

    def teardown(self):
        os.remove(TEST_CONFIG_FILEPATH)
