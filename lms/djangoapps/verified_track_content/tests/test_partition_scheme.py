from ..partition_scheme import EnrollmentTrackPartitionScheme, EnrollmentTrackUserPartition
from course_modes.models import CourseMode

from student.models import CourseEnrollment
from student.tests.factories import UserFactory
from verified_track_content.models import VerifiedTrackCohortedCourse
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.partitions.partitions import UserPartition


class EnrollmentTrackUserPartitionTest(SharedModuleStoreTestCase):

    @classmethod
    def setUpClass(cls):
        super(EnrollmentTrackUserPartitionTest, cls).setUpClass()
        cls.course = CourseFactory.create()

    def test_only_default_mode(self):
        self.assertEqual(len(self.course.user_partitions), 1)
        groups = self.course.user_partitions[0].groups
        self.assertEqual(1, len(groups))
        self.assertEqual("Audit", groups[0].name)

    def test_multiple_groups(self):
        def get_group_by_name(name):
            for group in self.course.user_partitions[0].groups:
                if group.name == name:
                    return group
            return None

        create_mode(self.course, CourseMode.AUDIT, "Audit Enrollment Track", min_price=0)
        create_mode(self.course, CourseMode.VERIFIED, "Verified Enrollment Track", min_price=1)
        create_mode(self.course, CourseMode.PROFESSIONAL, "Professional Enrollment Track", min_price=2)

        self.assertEqual(len(self.course.user_partitions), 1)
        groups = self.course.user_partitions[0].groups
        self.assertEqual(3, len(groups))
        self.assertIsNotNone(get_group_by_name("Audit Enrollment Track"))
        self.assertIsNotNone(get_group_by_name("Verified Enrollment Track"))
        self.assertIsNotNone(get_group_by_name("Professional Enrollment Track"))


class EnrollmentTrackPartitionSchemeTest(SharedModuleStoreTestCase):

    @classmethod
    def setUpClass(cls):
        super(EnrollmentTrackPartitionSchemeTest, cls).setUpClass()
        cls.course = CourseFactory.create()
        cls.student = UserFactory()

    def test_get_scheme(self):
        """
        Ensure that the scheme extension is correctly plugged in (via entry point in setup.py)
        """
        self.assertEquals(UserPartition.get_scheme('enrollment_track'), EnrollmentTrackPartitionScheme)

    def test_create_user_partition(self):
        user_partition = UserPartition.get_scheme('enrollment_track').create_user_partition(
            301, "partition", "test partition", parameters={"course_id": unicode(self.course.id)}
        )
        self.assertEqual(type(user_partition), EnrollmentTrackUserPartition)
        self.assertEqual(user_partition.name, "partition")

        groups = user_partition.groups
        self.assertEqual(1, len(groups))
        self.assertEqual("Audit", groups[0].name)

    def test_not_enrolled(self):
        self.assertIsNone(self._get_user_group())

    def test_default_enrollment(self):
        CourseEnrollment.enroll(self.student, self.course.id)
        self.assertEqual("Audit", self._get_user_group().name)

    def test_enrolled_in_nonexistent_mode(self):
        CourseEnrollment.enroll(self.student, self.course.id, mode=CourseMode.VERIFIED)
        self.assertEqual("Audit", self._get_user_group().name)

    def test_enrolled_in_verified(self):
        create_mode(self.course, CourseMode.VERIFIED, "Verified Enrollment Track", min_price=1)
        CourseEnrollment.enroll(self.student, self.course.id, mode=CourseMode.VERIFIED)
        self.assertEqual("Verified Enrollment Track", self._get_user_group().name)

    def test_using_verified_track_cohort(self):
        VerifiedTrackCohortedCourse.objects.create(course_key=self.course.id, enabled=True).save()
        CourseEnrollment.enroll(self.student, self.course.id)
        self.assertIsNone(self._get_user_group())

    def _get_user_group(self):
        user_partition = self.course.user_partitions[0]
        return user_partition.scheme.get_group_for_user(self.course.id, self.student, user_partition)


def create_mode(course, mode_slug, mode_name, min_price=0):
    """
    Create a new course mode
    """
    return CourseMode.objects.get_or_create(
        course_id=course.id,
        mode_display_name=mode_name,
        mode_slug=mode_slug,
        min_price=min_price,
        suggested_prices='',
        currency='usd'
    )