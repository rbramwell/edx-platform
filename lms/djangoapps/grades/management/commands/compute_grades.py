"""
Command to load course blocks.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.core.management.base import BaseCommand
import six

from openedx.core.lib.command_utils import (
    get_mutually_exclusive_required_option,
    validate_dependent_option,
    parse_course_keys,
)
#() from openedx.core.djangolib.waffle_utils import is_switch_enabled
from student.models import CourseEnrollment
from xmodule.modulestore.django import modulestore

from ... import tasks


log = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Example usage:
        $ ./manage.py lms compute_grades --all_courses --settings=devstack
        $ ./manage.py lms compute_grades 'edX/DemoX/Demo_Course' --settings=devstack
    """
    args = '<course_id course_id ...>'
    help = 'Computes and persists grade values for all learners in specified courses.'

    def add_arguments(self, parser):
        """
        Entry point for subclassed commands to add custom arguments.
        """
        parser.add_argument(
            '--courses',
            dest='courses',
            nargs='+',
            help='Generate course blocks for the list of courses provided.',
        )
        parser.add_argument(
            '--all_courses',
            help='Generate course blocks for all courses, given the requested start and end indices.',
            action='store_true',
            default=False,
        )
        parser.add_argument(
            '--enqueue_task',
            help='Enqueue the tasks for asynchronous computation.',
            action='store_true',
            default=False,
        )
        parser.add_argument(
            '--routing_key',
            dest='routing_key',
            help='Routing key to use for asynchronous computation.',
        )
        parser.add_argument(
            '--force_update',
            help='Force update of the course blocks for the requested courses.',
            action='store_true',
            default=False,
        )
        parser.add_argument(
            '--batch_size',
            help='Maximum number of students to calculate grades for, per celery task.',
            default=100,
            type=int,
        )
        parser.add_argument(
            '--start_index',
            help='Offset from which to start processing enrollments.',
            default=0,
            type=int,
        )

    def _get_course_keys(self, options):
        """
        Return a list of courses that need scores computed.
        """
        courses_mode = get_mutually_exclusive_required_option(options, 'courses', 'all_courses')
        if courses_mode == 'all_courses':
            course_keys = [course.id for course in modulestore().get_course_summaries()]
        else:
            course_keys = parse_course_keys(options['courses'])
        return course_keys

    def handle(self, *args, **options):

        validate_dependent_option(options, 'routing_key', 'enqueue_task')  # Do we want enqueue_task to be optional?

        self._set_log_level(options)

        for course_key in self._get_course_keys(options):
            self.enqueue_compute_grades_for_course(course_key, options)

    def enqueue_compute_grades_for_course_tasks(self, course_key, options):
        """
        Enqueue celery tasks to compute and persist all grades for the
        specified course, in batches.
        """
        enrollment_count = CourseEnrollment.objects.num_enrolled_in(course_key)
        for offset in six.moves.range(options['start_index'], enrollment_count, options['batch_size']):
            # If any new enrollments are added after the tasks are fired off, they are already persisting grades.
            # so there is no need to worry about race conditions.
            task_options = {'routing_key': options['routing_key']} if options.get('routing_key') else {}
            result = tasks.compute_grades_for_course.apply_async(
                kwargs={
                    'course_key': six.text_type(course_key),
                    'offset': offset,
                    'batch_size': options['batch_size'],
                },
                options=task_options,
            )
            log.info("Created task {task_id} for {course_key} [{offset}...{end}]".format(
                task_id=result.task_id,
                course_key=course_key,
                offset=offset,
                end=offset + options['batch_size'],
            ))

    def _set_log_level(self, options):
        """
        Sets logging levels for this module and the block structure
        cache module, based on the given the options.
        """
        if options.get('verbosity') == 0:
            log_level = logging.ERROR
        elif options.get('verbosity') == 1:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        log.setLevel(log_level)

