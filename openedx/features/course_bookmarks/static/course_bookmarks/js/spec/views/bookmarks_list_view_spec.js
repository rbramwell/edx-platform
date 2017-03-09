define(['backbone',
        'jquery',
        'underscore',
        'logger',
        'URI',
        'edx-ui-toolkit/js/utils/spec-helpers/ajax-helpers',
        'common/js/spec_helpers/template_helpers',
        'course_bookmarks/js/views/bookmarks_list_button',
        'course_bookmarks/js/views/bookmarks_list',
        'course_bookmarks/js/collections/bookmarks'],
    function(Backbone, $, _, Logger, URI, AjaxHelpers, TemplateHelpers, BookmarksListButtonView,
             BookmarksListView, BookmarksCollection) {
        'use strict';

        describe('lms.courseware.bookmarks', function() {
            var bookmarksButtonView, verifyRequestParams, createBookmarksData, createBookmarkUrl, breadcrumbTrail,
                verifyBookmarkedData, verifyPaginationInfo;

            beforeEach(function() {
                loadFixtures('course_bookmarks/fixtures/bookmarks.html');
                TemplateHelpers.installTemplates(
                    [
                        'templates/fields/message_banner'
                    ]
                );
                spyOn(Logger, 'log').and.returnValue($.Deferred().resolve());
                jasmine.addMatchers({
                    toHaveBeenCalledWithUrl: function() {
                        return {
                            compare: function(actual, expectedUrl) {
                                return {
                                    pass: expectedUrl === actual.calls.mostRecent().args[0].currentTarget.pathname
                                };
                            }
                        };
                    }
                });

                bookmarksButtonView = new BookmarksListButtonView();
            });

            verifyRequestParams = function(requests, params) {
                var urlParams = (new URI(requests[requests.length - 1].url)).query(true);
                _.each(params, function(value, key) {
                    expect(urlParams[key]).toBe(value);
                });
            };

            createBookmarksData = function(options) {
                var data = {
                        count: options.count || 0,
                        num_pages: options.num_pages || 1,
                        current_page: options.current_page || 1,
                        start: options.start || 0,
                        results: []
                    },
                    i, bookmarkInfo;

                for (i = 0; i < options.numBookmarksToCreate; i++) {
                    bookmarkInfo = {
                        id: i,
                        display_name: 'UNIT_DISPLAY_NAME_' + i,
                        created: new Date().toISOString(),
                        course_id: 'COURSE_ID',
                        usage_id: 'UNIT_USAGE_ID_' + i,
                        block_type: 'vertical',
                        path: [
                            {display_name: 'SECTION_DISAPLAY_NAME', usage_id: 'SECTION_USAGE_ID'},
                            {display_name: 'SUBSECTION_DISAPLAY_NAME', usage_id: 'SUBSECTION_USAGE_ID'}
                        ]
                    };

                    data.results.push(bookmarkInfo);
                }

                return data;
            };

            createBookmarkUrl = function(courseId, usageId) {
                return '/courses/' + courseId + '/jump_to/' + usageId;
            };

            breadcrumbTrail = function(path, unitDisplayName) {
                return _.pluck(path, 'display_name').
                concat([unitDisplayName]).
                join(' <span class="icon fa fa-caret-right" aria-hidden="true"></span><span class="sr">-</span> ');
            };

            verifyBookmarkedData = function(view, expectedData) {
                var courseId, usageId;
                var bookmarks = view.$('.bookmarks-results-list-item');
                var results = expectedData.results;
                var i, $bookmark;

                expect(bookmarks.length, results.length);

                for (i = 0; i < results.length; i++) {
                    $bookmark = $(bookmarks[i]);
                    courseId = results[i].course_id;
                    usageId = results[i].usage_id;

                    expect(bookmarks[i]).toHaveAttr('href', createBookmarkUrl(courseId, usageId));

                    expect($bookmark.data('bookmarkId')).toBe(i);
                    expect($bookmark.data('componentType')).toBe('vertical');
                    expect($bookmark.data('usageId')).toBe(usageId);

                    expect($bookmark.find('.list-item-breadcrumbtrail').html().trim())
                        .toBe(breadcrumbTrail(results[i].path, results[i].display_name));

                    expect($bookmark.find('.list-item-date').text().trim())
                        .toBe('Bookmarked on ' + view.humanFriendlyDate(results[i].created));
                }
            };

            verifyPaginationInfo = function(requests, expectedData, currentPage, headerMessage) {
                AjaxHelpers.respondWithJson(requests, expectedData);
                verifyBookmarkedData(bookmarksButtonView.bookmarksListView, expectedData);
                expect(bookmarksButtonView.bookmarksListView.$('.paging-footer span.current-page').text().trim()).
                toBe(currentPage);
                expect(bookmarksButtonView.bookmarksListView.$('.paging-header span').text().trim()).
                toBe(headerMessage);
            };

            it('has correct behavior for bookmarks button', function() {
                var requests = AjaxHelpers.requests(this);

                spyOn(bookmarksButtonView, 'toggleBookmarksListView').and.callThrough();

                bookmarksButtonView.delegateEvents();

                expect(bookmarksButtonView.$('.bookmarks-list-button')).toHaveAttr('aria-pressed', 'false');
                expect(bookmarksButtonView.$('.bookmarks-list-button')).toHaveClass('is-inactive');

                bookmarksButtonView.$('.bookmarks-list-button').click();
                expect(bookmarksButtonView.toggleBookmarksListView).toHaveBeenCalled();
                expect(bookmarksButtonView.$('.bookmarks-list-button')).toHaveAttr('aria-pressed', 'true');
                expect(bookmarksButtonView.$('.bookmarks-list-button')).toHaveClass('is-active');
                AjaxHelpers.respondWithJson(requests, createBookmarksData({numBookmarksToCreate: 1}));

                bookmarksButtonView.$('.bookmarks-list-button').click();
                expect(bookmarksButtonView.$('.bookmarks-list-button')).toHaveAttr('aria-pressed', 'false');
                expect(bookmarksButtonView.$('.bookmarks-list-button')).toHaveClass('is-inactive');
            });

            it('can correctly render an empty bookmarks list', function() {
                var requests = AjaxHelpers.requests(this);
                var expectedData = createBookmarksData({numBookmarksToCreate: 0});

                var emptyListText = 'Use bookmarks to help you easily return to courseware pages. ' +
                    'To bookmark a page, select Bookmark in the upper right corner of that page. ' +
                    'To see a list of all your bookmarks, select Bookmarks in the upper left ' +
                    'corner of any courseware page.';

                bookmarksButtonView.$('.bookmarks-list-button').click();
                AjaxHelpers.respondWithJson(requests, expectedData);

                expect(bookmarksButtonView.bookmarksListView.$('.bookmarks-empty-header').text().trim()).
                toBe('You have not bookmarked any courseware pages yet.');

                expect(bookmarksButtonView.bookmarksListView.$('.bookmarks-empty-detail-title').text().trim()).
                toBe(emptyListText);

                expect(bookmarksButtonView.bookmarksListView.$('.paging-header').length).toBe(0);
                expect(bookmarksButtonView.bookmarksListView.$('.paging-footer').length).toBe(0);
            });

            it('has rendered bookmarked list correctly', function() {
                var requests = AjaxHelpers.requests(this);
                var expectedData = createBookmarksData({numBookmarksToCreate: 3});

                bookmarksButtonView.$('.bookmarks-list-button').click();

                verifyRequestParams(
                    requests,
                    {course_id: 'a/b/c', fields: 'display_name,path', page: '1', page_size: '10'}
                );
                AjaxHelpers.respondWithJson(requests, expectedData);

                expect(bookmarksButtonView.bookmarksListView.$('.bookmarks-results-header').text().trim()).
                toBe('My Bookmarks');

                verifyBookmarkedData(bookmarksButtonView.bookmarksListView, expectedData);

                expect(bookmarksButtonView.bookmarksListView.$('.paging-header').length).toBe(1);
                expect(bookmarksButtonView.bookmarksListView.$('.paging-footer').length).toBe(1);
            });

            it('calls bookmarks list render on page_changed event', function() {
                var renderSpy = spyOn(BookmarksListView.prototype, 'render');
                var listView = new BookmarksListView({
                    collection: new BookmarksCollection([], {
                        course_id: 'abc',
                        url: '/test-bookmarks/url/'
                    })
                });
                listView.collection.trigger('page_changed');
                expect(renderSpy).toHaveBeenCalled();
            });

            it('can go to a page number', function() {
                var requests = AjaxHelpers.requests(this);
                var expectedData = createBookmarksData(
                    {
                        numBookmarksToCreate: 10,
                        count: 12,
                        num_pages: 2,
                        current_page: 1,
                        start: 0
                    }
                );

                bookmarksButtonView.$('.bookmarks-list-button').click();
                AjaxHelpers.respondWithJson(requests, expectedData);
                verifyBookmarkedData(bookmarksButtonView.bookmarksListView, expectedData);

                bookmarksButtonView.bookmarksListView.$('input#page-number-input').val('2');
                bookmarksButtonView.bookmarksListView.$('input#page-number-input').trigger('change');

                expectedData = createBookmarksData(
                    {
                        numBookmarksToCreate: 2,
                        count: 12,
                        num_pages: 2,
                        current_page: 2,
                        start: 10
                    }
                );
                AjaxHelpers.respondWithJson(requests, expectedData);
                verifyBookmarkedData(bookmarksButtonView.bookmarksListView, expectedData);

                expect(bookmarksButtonView.bookmarksListView.$('.paging-footer span.current-page').text().trim()).
                toBe('2');
                expect(bookmarksButtonView.bookmarksListView.$('.paging-header span').text().trim()).
                toBe('Showing 11-12 out of 12 total');
            });

            it('can navigate forward and backward', function() {
                var requests = AjaxHelpers.requests(this);
                var expectedData = createBookmarksData(
                    {
                        numBookmarksToCreate: 10,
                        count: 15,
                        num_pages: 2,
                        current_page: 1,
                        start: 0
                    }
                );

                bookmarksButtonView.$('.bookmarks-list-button').click();
                verifyPaginationInfo(requests, expectedData, '1', 'Showing 1-10 out of 15 total');
                verifyRequestParams(
                    requests,
                    {course_id: 'a/b/c', fields: 'display_name,path', page: '1', page_size: '10'}
                );

                bookmarksButtonView.bookmarksListView.$('.paging-footer .next-page-link').click();
                expectedData = createBookmarksData(
                    {
                        numBookmarksToCreate: 5,
                        count: 15,
                        num_pages: 2,
                        current_page: 2,
                        start: 10
                    }
                );
                verifyPaginationInfo(requests, expectedData, '2', 'Showing 11-15 out of 15 total');
                verifyRequestParams(
                    requests,
                    {course_id: 'a/b/c', fields: 'display_name,path', page: '2', page_size: '10'}
                );

                expectedData = createBookmarksData(
                    {
                        numBookmarksToCreate: 10,
                        count: 15,
                        num_pages: 2,
                        current_page: 1,
                        start: 0
                    }
                );
                bookmarksButtonView.bookmarksListView.$('.paging-footer .previous-page-link').click();
                verifyPaginationInfo(requests, expectedData, '1', 'Showing 1-10 out of 15 total');
                verifyRequestParams(
                    requests,
                    {course_id: 'a/b/c', fields: 'display_name,path', page: '1', page_size: '10'}
                );
            });

            it('can navigate to correct url', function() {
                var requests = AjaxHelpers.requests(this),
                    url;
                spyOn(bookmarksButtonView.bookmarksListView, 'visitBookmark');

                bookmarksButtonView.$('.bookmarks-list-button').click();
                AjaxHelpers.respondWithJson(requests, createBookmarksData({numBookmarksToCreate: 1}));

                bookmarksButtonView.bookmarksListView.$('.bookmarks-results-list-item').click();
                url = bookmarksButtonView.bookmarksListView.$('.bookmarks-results-list-item').attr('href');
                expect(bookmarksButtonView.bookmarksListView.visitBookmark).toHaveBeenCalledWithUrl(url);
            });

            it('shows an error message for HTTP 500', function() {
                var requests = AjaxHelpers.requests(this);

                bookmarksButtonView.$('.bookmarks-list-button').click();

                AjaxHelpers.respondWithError(requests);

                expect(bookmarksButtonView.bookmarksListView.$('.bookmarks-results-header').text().trim()).not
                    .toBe('My Bookmarks');
                expect($('#error-message').text().trim()).toBe(bookmarksButtonView.bookmarksListView.errorMessage);
            });
        });
    });
