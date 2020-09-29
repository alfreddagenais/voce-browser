#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 18:09:34 2020

@author: trabdlkarim
"""


from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView , QWebEnginePage, QWebEngineSettings
from PyQt5.QtWebEngineWidgets import QWebEngineProfile

from vocebrowser.browserui import BrowserUi
from vocebrowser.assistant.voce import VoceAssistant


class WebView(QWebEngineView):

    devToolsRequested = QtCore.pyqtSignal(QWebEnginePage)

    def __init__(self,parent=None):
        self.parent = parent
        super(WebView,self).__init__(parent)

    def contextMenuEvent(self, event):
        menu  = self.page().createStandardContextMenu()
        actions = menu.actions()
        inspectElement =  self.page().action(QWebEnginePage.InspectElement)
        if inspectElement not in actions:
            action = QtWidgets.QAction()
            action.setText("Inspect")
            action.triggered.connect(lambda: self.devToolsRequested.emit(self.page()) )
            menu.addAction(action)
        menu.exec_(event.globalPos())

    def createWindow(self, winType):
        if winType == QWebEnginePage.WebBrowserTab:
           return self.parent.open_new_tab()
        elif winType == QWebEnginePage.WebBrowserWindow:
            return VoceBrowser.create_browser_window()

    def reload(self):
        super().reload()
        url = self.page().url()
        self.parent.ui.urlbar.setText(url.toString())



class BrowserWindow(QtWidgets.QMainWindow):
    VOCE_INITIALIZED = False
    def __init__(self,*args,**kwargs):
        super(BrowserWindow, self).__init__(*args, **kwargs)

        self.home_url = QUrl('https://duckduckgo.com/')
        self.appName = "Voce Browser"

        self.assistant = VoceAssistant()


        self.profile = QWebEngineProfile(self)
        self.ui = BrowserUi()
        self.ui.setupUi(self)

        self.ui.urlbar.returnPressed.connect(self.goto_current_url)
        self.ui.goButton.clicked.connect(self.goto_current_url)

        self.ui.actionExit.triggered.connect(self.close)

        self.ui.actionNewWindow.triggered.connect(self.onclick_new_window)
        self.ui.actionNewTab.triggered.connect(self.open_new_tab)
        self.ui.actionBack.triggered.connect(lambda:self.ui.tabWidget.currentWidget().back())
        self.ui.actionForward.triggered.connect(lambda:self.ui.tabWidget.currentWidget().forward())
        self.ui.actionReload.triggered.connect(lambda:self.ui.tabWidget.currentWidget().reload())
        self.ui.actionHome.triggered.connect(self.go_home)

        self.ui.tabWidget.currentChanged.connect(self.onchange_current_tab)
        self.ui.tabWidget.tabCloseRequested.connect(self.onclose_tab)

        self.setCentralWidget(self.ui.centralwidget)

        self.assistant.signals.welcome.connect(self.assistant.welcome)
        self.assistant.signals.openNewTab.connect(self.open_new_tab)
        self.assistant.signals.closeCurrentTab.connect(lambda: self.onclose_tab(self.ui.tabWidget.currentIndex()))

        self.assistant.signals.openNewWindow.connect(self.onclick_new_window)
        self.assistant.signals.closeCurrentWindow.connect(self.close)

        self.ass_process = AssistantRunnable(self.assistant.run_forever)



    def open_new_tab(self,url=None, title="New Tab"):
        webView = WebView(self)
        webPage = QWebEnginePage(self.profile,webView)
        webView.setPage(webPage)
        if url:
            webView.page().setUrl(url)
        webView.setFocus()

        index = self.ui.tabWidget.addTab(webView, title)
        self.ui.tabWidget.setCurrentIndex(index)
        webView.urlChanged.connect(lambda qurl, view = webView: self.update_address_bar(qurl, view))
        webView.titleChanged.connect(lambda _, i = index, view = webView:self.update_tab_title(i, view))
        webView.iconChanged.connect(lambda _,i=index,view=webView:self.update_favIcon(i,view))
        webView.loadFinished.connect(self.init_voce)
        webView.devToolsRequested.connect(self.showDevToolsPage)

        webView.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        webView.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        webView.settings().setAttribute(QWebEngineSettings.ErrorPageEnabled, True)
        webView.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)

        return webView


    def init_voce(self,isCompleted):
        if isCompleted:
            if not BrowserWindow.VOCE_INITIALIZED:
                self.assistant.signals.welcome.emit()
                BrowserWindow.VOCE_INITIALIZED = True
                self.ass_process.start()



    def update_favIcon(self,tabIndex,webView):
        self.ui.tabWidget.setTabIcon(tabIndex, webView.icon())

    def update_tab_title(self, tabIndex, webView):
        title = webView.page().title()
        self.setWindowTitle("%s - %s" % (title,self.appName))
        self.ui.tabWidget.setTabText(tabIndex, title)

    def onchange_current_tab(self, i):
        qurl = self.ui.tabWidget.currentWidget().url()
        self.update_address_bar(qurl, self.ui.tabWidget.currentWidget())
        self.update_browser_title(self.ui.tabWidget.currentWidget())

    def onclose_tab(self, i):
        if self.ui.tabWidget.count() < 2:
            self.close()
        else:
            self.ui.tabWidget.removeTab(i)

    def onclick_new_tab(self,i):
        if i == -1:
            webView = self.open_new_tab()
            self.update_browser_title(webView)

    def onclick_new_window(self):
        new_window = BrowserWindow()
        new_window.open_new_tab(self.home_url)
        new_window.show()

    def update_address_bar(self, new_url, view=None):
        if view != self.ui.tabWidget.currentWidget():
            return
        self.ui.urlbar.setText(new_url.toString())
        #self.ui.urlbar.selectAll()

    def update_browser_title(self, view):
        if view != self.ui.tabWidget.currentWidget():
            return
        title = self.ui.tabWidget.currentWidget().page().title()
        if not title.strip():
            title = "New Tab"
        self.setWindowTitle("%s - %s" % (title,self.appName))

    def go_home(self):
        self.ui.tabWidget.currentWidget().setUrl(self.home_url)
        url = self.ui.tabWidget.currentWidget().page().url()
        self.ui.urlbar.setText(url.toString())

    def goto_current_url(self):
        current_url = QUrl.fromUserInput(self.ui.urlbar.text())
        if current_url.isValid():
            if not '.' in self.ui.urlbar.text():
                current_url = self.create_search_query("https://duckduckgo.com",self.ui.urlbar.text())
        else:
            current_url = self.create_search_query("https://duckduckgo.com",self.ui.urlbar.text())

        self.ui.tabWidget.currentWidget().setUrl(current_url)

    def create_search_query(self,engine,keywords):
        query = engine + "?q="
        words = keywords.split()
        count = len(words)
        for w in words:
            if count>1:
                query += w + '+'
            else:
                query += w
            count -= 1
        return QUrl(query)

    def closeEvent(self, event):
        answer = QMessageBox.question(self,"Quit", "Are you sure you want to close this window?",
                            QMessageBox.Yes | QMessageBox.No)

        if answer == QMessageBox.Yes:
            event.accept()
            self.deleteLater()
            self.assistant.stop_event.set()
           # QtWidgets.QApplication.quit()

        else:
            event.ignore()


    def showDevToolsPage(self,page):
        devToolsView = QWebEngineView()
        page.setDevToolsPage(devToolsView.page()) # same as devToolsView.setInspectedPage(page)
        i = self.ui.tabWidget.addTab(devToolsView, page.title())
        self.ui.tabWidget.setCurrentIndex(i)


class VoceBrowser(object):

    home_url = QUrl('https://duckduckgo.com/')
    appName = "Voce Browser"

    @staticmethod
    def create_browser_window(url=None, offRecord=False):
        window = BrowserWindow()
        if not url :
            url = VoceBrowser.home_url
        webView = window.open_new_tab(url)
        window.show()
        return webView

    def launch(self):
        VoceBrowser.create_browser_window(VoceBrowser.home_url)



class AssistantRunnable(QtCore.QRunnable):
    def __init__(self,target,*args,**kwargs):
        super(AssistantRunnable,self).__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.target(*self.args,**self.kwargs)

    def start(self):
        QtCore.QThreadPool.globalInstance().start(self)