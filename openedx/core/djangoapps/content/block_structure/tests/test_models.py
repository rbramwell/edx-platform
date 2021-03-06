"""
Unit tests for Block Structure models.
"""
# pylint: disable=protected-access
import ddt
from django.test import TestCase
from django.utils.timezone import now
from itertools import product
from mock import patch, Mock
from uuid import uuid4

from opaque_keys.edx.locator import CourseLocator, BlockUsageLocator

from ..config import PRUNE_OLD_VERSIONS
from ..exceptions import BlockStructureNotFound
from ..models import BlockStructureModel
from .helpers import override_config_setting


@ddt.ddt
class BlockStructureModelTestCase(TestCase):
    """
    Tests for BlockStructureModel.
    """
    def setUp(self):
        super(BlockStructureModelTestCase, self).setUp()
        self.course_key = CourseLocator('org', 'course', unicode(uuid4()))
        self.usage_key = BlockUsageLocator(course_key=self.course_key, block_type='course', block_id='course')

        self.params = self._create_bsm_params()

    def tearDown(self):
        with override_config_setting(PRUNE_OLD_VERSIONS, active=True):
            BlockStructureModel._prune_files(self.usage_key, num_to_keep=0)
        super(BlockStructureModelTestCase, self).tearDown()

    def _assert_bsm_fields(self, bsm, expected_serialized_data):
        """
        Verifies that the field values and serialized data
        on the given bsm are as expected.
        """
        for field_name, field_value in self.params.iteritems():
            self.assertEqual(field_value, getattr(bsm, field_name))

        self.assertEqual(bsm.get_serialized_data(), expected_serialized_data)
        self.assertIn(unicode(self.usage_key), bsm.data.name)

    def _assert_file_count_equal(self, expected_count):
        """
        Asserts the number of files for self.usage_key
        is as expected.
        """
        self.assertEqual(len(BlockStructureModel._get_all_files(self.usage_key)), expected_count)

    def _create_bsm_params(self):
        """
        Returns the parameters for creating a BlockStructureModel.
        """
        return dict(
            data_usage_key=self.usage_key,
            data_version='DV',
            data_edit_timestamp=now(),
            transformers_schema_version='TV',
            block_structure_schema_version=unicode(1),
        )

    def _verify_update_or_create_call(self, serialized_data, mock_log=None, expect_created=None):
        """
        Calls BlockStructureModel.update_or_create
        and verifies the response.
        """
        bsm, created = BlockStructureModel.update_or_create(serialized_data, **self.params)
        if mock_log:
            self.assertEqual("Created" if expect_created else "Updated", mock_log.info.call_args[0][1])
            self.assertEqual(len(serialized_data), mock_log.info.call_args[0][3])
        self._assert_bsm_fields(bsm, serialized_data)
        if expect_created is not None:
            self.assertEqual(created, expect_created)
        return bsm

    @patch('openedx.core.djangoapps.content.block_structure.models.log')
    def test_update_or_create(self, mock_log):
        serialized_data = 'initial data'

        # shouldn't already exist
        with self.assertRaises(BlockStructureNotFound):
            BlockStructureModel.get(self.usage_key)
            self.assertIn("BlockStructure: Not found in table;", mock_log.info.call_args[0][0])

        # create an entry
        bsm = self._verify_update_or_create_call(serialized_data, mock_log, expect_created=True)

        # get entry
        found_bsm = BlockStructureModel.get(self.usage_key)
        self._assert_bsm_fields(found_bsm, serialized_data)
        self.assertIn("BlockStructure: Read data from store;", mock_log.info.call_args[0][0])

        # update entry
        self.params.update(dict(data_version='new version'))
        updated_serialized_data = 'updated data'
        updated_bsm = self._verify_update_or_create_call(updated_serialized_data, mock_log, expect_created=False)
        self.assertNotEqual(bsm.data.name, updated_bsm.data.name)

        # old files not pruned
        self._assert_file_count_equal(2)

    @override_config_setting(PRUNE_OLD_VERSIONS, active=True)
    @patch('openedx.core.djangoapps.content.block_structure.config.num_versions_to_keep', Mock(return_value=1))
    def test_prune_files(self):
        self._verify_update_or_create_call('test data', expect_created=True)
        self._verify_update_or_create_call('updated data', expect_created=False)
        self._assert_file_count_equal(1)

    @override_config_setting(PRUNE_OLD_VERSIONS, active=True)
    @patch('openedx.core.djangoapps.content.block_structure.config.num_versions_to_keep', Mock(return_value=1))
    @patch('openedx.core.djangoapps.content.block_structure.models.BlockStructureModel._delete_files')
    @patch('openedx.core.djangoapps.content.block_structure.models.log')
    def test_prune_exception(self, mock_log, mock_delete):
        mock_delete.side_effect = Exception
        self._verify_update_or_create_call('test data', expect_created=True)
        self._verify_update_or_create_call('updated data', expect_created=False)

        self.assertIn('BlockStructure: Exception when deleting old files', mock_log.exception.call_args[0][0])
        self._assert_file_count_equal(2)  # old files not pruned

    @ddt.data(
        *product(
            range(1, 3),  # prune_keep_count
            range(4),  # num_prior_edits
        )
    )
    @ddt.unpack
    def test_prune_keep_count(self, prune_keep_count, num_prior_edits):
        with patch(
            'openedx.core.djangoapps.content.block_structure.config.num_versions_to_keep',
            return_value=prune_keep_count,
        ):
            for _ in range(num_prior_edits):
                self._verify_update_or_create_call('data')

            if num_prior_edits:
                self._assert_file_count_equal(num_prior_edits)

            with override_config_setting(PRUNE_OLD_VERSIONS, active=True):
                self._verify_update_or_create_call('data')
                self._assert_file_count_equal(min(prune_keep_count, num_prior_edits + 1))
