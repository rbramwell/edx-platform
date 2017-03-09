"""
Views to show a course's bookmarks.
"""

from django.contrib.auth.decorators import login_required
from django.core.context_processors import csrf
from django.shortcuts import render_to_response
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import View

from courseware.courses import get_course_with_access
from opaque_keys.edx.keys import CourseKey
from util.views import ensure_valid_course_key
from web_fragments.fragment import Fragment
from web_fragments.views import FragmentView
from xmodule.modulestore.django import modulestore


class CourseBookmarksView(View):
    """
    The home page for a course.
    """
    @method_decorator(login_required)
    @method_decorator(ensure_csrf_cookie)
    @method_decorator(cache_control(no_cache=True, no_store=True, must_revalidate=True))
    @method_decorator(ensure_valid_course_key)
    def get(self, request, course_id):
        """
        Displays the home page for the specified course.

        Arguments:
            request: HTTP request
            course_id (unicode): course id
        """
        course_key = CourseKey.from_string(course_id)
        course = get_course_with_access(request.user, 'load', course_key, check_if_enrolled=True)

        # Render the bookmarks list as a fragment
        outline_fragment = CourseBookmarksFragmentView().render_to_fragment(request, course_id=course_id)

        # Render the entire unified course view
        context = {
            'csrf': csrf(request)['csrf_token'],
            'course': course,
            'outline_fragment': outline_fragment,
            'disable_courseware_js': True,
            'uses_pattern_library': True,
        }
        return render_to_response('course_bookmarks/course-bookmarks.html', context)


class CourseBookmarksFragmentView(FragmentView):
    """
    Course outline fragment to be shown in the unified course view.
    """

    def populate_children(self, block, all_blocks):
        """
        For a passed block, replace each id in its children array with the full representation of that child,
        which will be looked up by id in the passed all_blocks dict.
        Recursively do the same replacement for children of those children.
        """
        children = block.get('children') or []

        for i in range(len(children)):
            child_id = block['children'][i]
            child_detail = self.populate_children(all_blocks[child_id], all_blocks)
            block['children'][i] = child_detail

        return block

    def render_to_fragment(self, request, course_id=None, **kwargs):
        """
        Renders the course outline as a fragment.
        """
        course_key = CourseKey.from_string(course_id)
        course = get_course_with_access(request.user, 'load', course_key, check_if_enrolled=True)
        course_usage_key = modulestore().make_course_usage_key(course_key)

        context = {
            'csrf': csrf(request)['csrf_token'],
            'course': course,
        }
        html = render_to_string('course_bookmarks/course-bookmarks-fragment.html', context)
        return Fragment(html)
