from cgi import escape
from urllib import quote_plus

from zope.interface import implements, alsoProvides
from zope.component import getMultiAdapter
from zope.viewlet.interfaces import IViewlet
from zope.deprecation.deprecation import deprecate

from AccessControl import getSecurityManager
from Acquisition import aq_base, aq_inner
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.app.layout.globals.interfaces import IViewView


def get_language(context, request):
    portal_state = getMultiAdapter((context, request),
                                   name=u'plone_portal_state')
    return portal_state.locale().getLocaleID()


class ViewletBase(BrowserView):
    """ Base class with common functions for link viewlets.
    """
    implements(IViewlet)

    def __init__(self, context, request, view, manager=None):
        super(ViewletBase, self).__init__(context, request)
        self.__parent__ = view
        self.context = context
        self.request = request
        self.view = view
        self.manager = manager

    @property
    @deprecate("Use site_url instead. ViewletBase.portal_url will be removed in Plone 4")
    def portal_url(self):
        return self.site_url


    def update(self):
        self.portal_state = getMultiAdapter((self.context, self.request),
                                            name=u'plone_portal_state')
        self.site_url = self.portal_state.portal_url()

    def render(self):
        # defer to index method, because that's what gets overridden by the template ZCML attribute
        return self.index()
        
    def index(self):
        raise NotImplementedError(
            '`index` method must be implemented by subclass.')


class TitleViewlet(ViewletBase):

    def update(self):
        self.portal_state = getMultiAdapter((self.context, self.request),
                                            name=u'plone_portal_state')
        self.context_state = getMultiAdapter((self.context, self.request),
                                             name=u'plone_context_state')
        self.page_title = self.context_state.object_title
        self.portal_title = self.portal_state.portal_title

    def index(self):
        portal_title = safe_unicode(self.portal_title())
        page_title = safe_unicode(self.page_title())
        if page_title == portal_title:
            return u"<title>%s</title>" % (escape(portal_title))
        else:
            return u"<title>%s &mdash; %s</title>" % (
                escape(safe_unicode(page_title)),
                escape(safe_unicode(portal_title)))


class TableOfContentsViewlet(ViewletBase):
    index = ViewPageTemplateFile('toc.pt')

    def update(self):
        obj = aq_base(self.context)
        getTableContents = getattr(obj, 'getTableContents', None)
        self.enabled = False
        if getTableContents is not None:
            try:
                self.enabled = getTableContents()
            except KeyError:
                # schema not updated yet
                self.enabled = False


class SkipLinksViewlet(ViewletBase):
    index = ViewPageTemplateFile('skip_links.pt')

    def update(self):
        context_state = getMultiAdapter((self.context, self.request),
                                        name=u'plone_context_state')
        self.current_page_url = context_state.current_page_url


class SiteActionsViewlet(ViewletBase):
    index = ViewPageTemplateFile('site_actions.pt')

    def controlpanel(self):
        return getSecurityManager().checkPermission('Manage portal', self.context)


class SearchBoxViewlet(ViewletBase):
    index = ViewPageTemplateFile('searchbox.pt')

    def update(self):
        super(SearchBoxViewlet, self).update()

        context_state = getMultiAdapter((self.context, self.request),
                                        name=u'plone_context_state')

        props = getToolByName(self.context, 'portal_properties')
        livesearch = props.site_properties.getProperty('enable_livesearch', False)
        if livesearch:
            self.search_input_id = "searchGadget"
        else:
            self.search_input_id = ""

        folder = context_state.folder()
        self.folder_path = '/'.join(folder.getPhysicalPath())


class LogoViewlet(ViewletBase):
    index = ViewPageTemplateFile('logo.pt')

    def update(self):
        super(LogoViewlet, self).update()

        self.navigation_root_url = self.portal_state.navigation_root_url()

        portal = self.portal_state.portal()
        self.logo_tag = portal.restrictedTraverse('logo.jpg').tag()

        self.portal_title = self.portal_state.portal_title()


class GlobalSectionsViewlet(ViewletBase):
    index = ViewPageTemplateFile('sections.pt')


class PersonalBarViewlet(ViewletBase):
    index = ViewPageTemplateFile('personal_bar.pt')

    def update(self):
        super(PersonalBarViewlet, self).update()
        context = aq_inner(self.context)

        context_state = getMultiAdapter((context, self.request),
                                        name=u'plone_context_state')

        self.user_actions = context_state.actions('user')
        self.anonymous = self.portal_state.anonymous()
        self.available = self.user_actions or not self.anonymous

        if not self.anonymous:
            member = self.portal_state.member()
            userid = member.getId()

            sm = getSecurityManager()
            if sm.checkPermission('Portlets: Manage own portlets', context):
                self.homelink_url = self.site_url + '/dashboard'
            else:
                if userid.startswith('http:') or userid.startswith('https:'):
                    self.homelink_url = self.site_url + '/author/?author=' + userid
                else:
                    self.homelink_url = self.site_url + '/author/' + quote_plus(userid)

            membership = getToolByName(context, 'portal_membership')
            member_info = membership.getMemberInfo(member.getId())
            # member_info is None if there's no Plone user object, as when
            # using OpenID.
            if member_info:
                fullname = member_info.get('fullname', '')
            else:
                fullname = None
            if fullname:
                self.user_name = fullname
            else:
                self.user_name = userid


class PathBarViewlet(ViewletBase):

    render = ViewPageTemplateFile('path_bar.pt')

    @property
    def navigation_root_url(self):
        return self.portal_state.navigation_root_url()

    @property
    def is_rtl(self):
        return self.portal_state.is_rtl()

    @property
    def breadcrumbs(self):
        context = aq_inner(self.context)
        breadcrumbs_view = getMultiAdapter((context, self.request),
                                           name='breadcrumbs_view')
        return breadcrumbs_view.breadcrumbs()


class ContentActionsViewlet(ViewletBase):
    index = ViewPageTemplateFile('contentactions.pt')
    
    def update(self):
        context = aq_inner(self.context)
        context_state = getMultiAdapter((context, self.request),
                                        name=u'plone_context_state')

        self.object_actions = context_state.actions('object_actions')
        
        # The drop-down menus are pulled in via a simple content provider
        # from plone.app.contentmenu. This behaves differently depending on
        # whether the view is marked with IViewView. If our parent view 
        # provides that marker, we should do it here as well.
        if IViewView.providedBy(self.__parent__):
            alsoProvides(self, IViewView)


class ColophonViewlet(ViewletBase):

    render = ViewPageTemplateFile('colophon.pt')
