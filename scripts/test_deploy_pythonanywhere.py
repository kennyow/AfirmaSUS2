import unittest
from unittest.mock import Mock, patch

from scripts.deploy_pythonanywhere import (
    Client, code_file, validate_requirements, same_migration, error_annotation,
    data_file, destination, validate_json, publish_data,
)


class DeploymentTests(unittest.TestCase):
    def test_json_routes_to_live_data_directory(self):
        self.assertTrue(data_file('linhadotempodinamica.json'))
        self.assertEqual(destination('timeline.json'), '/home/kennyow/afirmasus-dados/timeline.json')
        for name in ['../timeline.json', '/timeline.json', '.secret.json', 'media/a.json', 'db.sqlite3']:
            self.assertFalse(data_file(name))

    def test_invalid_json_blocks_publication(self):
        validate_json('timeline.json', b'{"events": []}')
        for content in [b'{', b'{"value": NaN}', b'\xff']:
            with self.assertRaisesRegex(RuntimeError, 'JSON inválido'):
                validate_json('timeline.json', content)

    def test_data_backup_is_verified_before_overwrite(self):
        client = Mock()
        client.read.side_effect = [b'old', b'old', b'old', b'new']
        publish_data(client, 'timeline.json', b'new', b'old', '/backup')
        self.assertEqual(client.write.call_args_list[0].args, ('/backup/timeline.json', b'old'))
        self.assertEqual(client.write.call_args_list[1].args,
                         ('/home/kennyow/afirmasus-dados/timeline.json', b'new'))

    def test_backup_failure_prevents_data_overwrite(self):
        client = Mock()
        client.read.side_effect = [b'old', b'bad backup']
        with self.assertRaises(RuntimeError):
            publish_data(client, 'timeline.json', b'new', b'old', '/backup')
        self.assertEqual(client.write.call_count, 1)

    def test_concurrent_site_edit_prevents_data_overwrite(self):
        client = Mock()
        client.read.return_value = b'changed by site'
        with self.assertRaises(RuntimeError):
            publish_data(client, 'timeline.json', b'new', b'old', '/backup')
        client.write.assert_not_called()

    def test_migration_comments_bom_and_line_endings_do_not_block(self):
        self.assertTrue(same_migration(
            b'# Generated yesterday\noperations = [CreateModel(name="Example")]\n',
            b'\xef\xbb\xbf# Generated today\r\noperations=[CreateModel(name=\'Example\')]\r\n',
        ))

    def test_actual_migration_changes_remain_blocked(self):
        self.assertFalse(same_migration(b'operations = [CreateModel(name="A")]',
                                        b'operations = [CreateModel(name="B")]'))
        self.assertFalse(same_migration(b'operations = []', None))
        self.assertFalse(same_migration(b'operations = []', b'invalid syntax !'))

    def test_annotation_escapes_special_characters(self):
        self.assertEqual(error_annotation('erro%\nsegunda linha\rfim'),
                         '::error::erro%25%0Asegunda linha%0Dfim')

    def test_requirements_formatting_does_not_block_deployment(self):
        validate_requirements(b'Django==5.2.18\nrequests==2.34.2\n',
                              b'\xef\xbb\xbf# dependencies\r\nrequests==2.34.2\r\n Django==5.2.18 \r\n')

    def test_dependency_changes_still_block_deployment(self):
        with self.assertRaisesRegex(RuntimeError, 'difere do GitHub'):
            validate_requirements(b'Django==5.2.18', b'Django==5.2.17')

    def test_missing_requirements_has_specific_diagnostic(self):
        with self.assertRaisesRegex(RuntimeError, 'Arquivo ausente'):
            validate_requirements(b'Django==5.2.18', None)

    def test_data_and_credentials_are_excluded(self):
        for name in ['db.sqlite3', 'timeline.json', 'linhadotempodinamica.json',
                     'media/upload.png', '.env', 'setup/.secret.py',
                     'core/data.json', '../setup/settings.py', '/setup/settings.py',
                     'core/__pycache__/views.py', '.git/config']:
            with self.subTest(name=name):
                self.assertFalse(code_file(name))

    def test_application_sources_are_included(self):
        for name in ['setup/settings.py', 'core/views.py',
                     'core/templates/core/index.html', 'static/logo.png']:
            self.assertTrue(code_file(name))

    @patch('scripts.deploy_pythonanywhere.time.sleep')
    def test_authentication_errors_stop_deployment(self, sleep):
        client = Client('test-token')
        response = Mock(status_code=403)
        response.raise_for_status.side_effect = RuntimeError('403')
        client.session.request = Mock(return_value=response)
        with self.assertRaises(RuntimeError):
            client.read('/example')

    @patch('scripts.deploy_pythonanywhere.time.sleep')
    def test_missing_remote_file_is_distinct_from_empty_file(self, sleep):
        client = Client('test-token')
        client.session.request = Mock(return_value=Mock(status_code=404))
        self.assertIsNone(client.read('/missing'))
        client.session.request = Mock(return_value=Mock(status_code=200, content=b''))
        self.assertEqual(client.read('/empty'), b'')


if __name__ == '__main__':
    unittest.main()
