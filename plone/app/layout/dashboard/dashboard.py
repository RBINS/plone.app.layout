from zope.component import getUtility

from Products.Five.browser import BrowserView

from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IColumnManager
from plone.portlets.constants import USER_CATEGORY

from plone.memoize.instance import memoize

from Products.CMFCore.utils import getToolByName


class DashboardView(BrowserView):
    """Power the dasbhard
    """

    @memoize
    def empty(self):
        dashboards = [getUtility(IPortletManager, name=name) for name in
                        getUtility(IColumnManager, 'plone.dashboard')]

        portal_membership = getToolByName(self.context, 'portal_membership')
        userid = portal_membership.getAuthenticatedMember().getId()

        num_portlets = 0
        for dashboard in dashboards:
            num_portlets += len(dashboard.get(USER_CATEGORY, {}).get(userid, {}))
        return num_portlets == 0
    
    def list_columns(self):
        return getUtility(IColumnManager, 'plone.dashboard')
