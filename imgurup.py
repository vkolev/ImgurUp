#!/usr/bin/env python
#-*- encoding: utf-8 -*-

import os
import sys
import dbus
import dbus.service
import dbus.glib
try:
    import simplejson
except:
    print "You don't have python-simplejson installed"
import base64
try:
    import gtk
    import pygtk
    pygtk.require('2.0')
except:
    print "You don't have pyGTK installed"
import urllib
import urllib2
try:
    from pysqlite2 import dbapi2 as sqlite
except:
    print "You don't have pysqlite2 installed"
try:
    from configobj import ConfigObj
except:
    print "You dont' have python-configobj installed"
import webbrowser

'''
Simple desktop app for uploading image to Imgur.com
@author: Vladimir Kolev
'''

__author__ = "Vladimir Kolev <vladimir.r.kolev@gmail.com>"
__doc__ = '''Desktop application for uploading images to the
 Imgur.com website\n\nYou will need a developer API key!
 Be awere that there is a <<50 Uploads>> per hour!'''
__version__ = "1.0"

basepath = os.path.abspath(os.path.dirname(sys.argv[0]))

builder = gtk.Builder()
builder.add_from_file("%s/data/main.ui" % basepath)
config = ConfigObj("%s/data/imgurup_config.ini" % basepath)

class MainApp:
    
    def __init__(self):
        self.window = builder.get_object('window1')
        self.window.connect('delete-event', self.window_close)
        self.windowstate = 1
        self.filebtn = builder.get_object('filechoose')
        self.filefilter = builder.get_object('filefilter1')
        self.filefilter.set_name("Image Files")
        self.filefilter.add_pixbuf_formats()
        self.filebtn.set_filter(self.filefilter)
        self.filebtn.connect('file-set', self.set_image_title)
        self.title_entry = builder.get_object('title_entry')
        self.header = builder.get_object('headerimg')

        self.logbtn = builder.get_object('logbtn')
        self.logbtn.connect('clicked', self.show_logview)

        self.aboutbtn = builder.get_object('aboutbtn')
        self.aboutbtn.connect('clicked', self.show_about)

        self.clearbtn = builder.get_object('clearbtn')
        self.clearbtn.connect('clicked', self.clear_fields)

        self.upbtn = builder.get_object('upbtn')
        self.upbtn.connect('clicked', self.upload)

        self.statusicon = gtk.StatusIcon()
        self.statusicon.set_from_file('%s/data/imgurup_16.png' % basepath)
        self.statusicon.connect("popup-menu", self.right_click_event)
        self.statusicon.connect("activate", self.icon_clicked)
        self.statusicon.set_tooltip("Imgur Uploader")

        self.window.show_all()

    def window_destroy(self, widget, data=None):
        quitdiag = gtk.MessageDialog(None, 
        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
        gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, 
        "Really quit from ImgurUp?")
        quitdiag.set_title("Exit?")
        response = quitdiag.run()
        if response == gtk.RESPONSE_YES:
            gtk.main_quit()
        else:
            quitdiag.destroy()
        
    def window_close(self, widget, data=None):
        self.window.hide_on_delete()
        self.windowstate = 0
        return True

    def show_about(self, widget, data=None):
        about_dialog = gtk.AboutDialog()
        about_dialog.set_icon_from_file("%s/data/imgurup_24.png" % basepath)
        about_dialog.set_program_name("Imgur Uploader")
        about_dialog.set_version(__version__)
        about_dialog.set_copyright("2011 (c) Vladimir Kolev")
        about_dialog.set_comments(__doc__)
        licensestr = open("%s/LICENSE" % basepath, 'r').read()
        about_dialog.set_license(licensestr)
        about_dialog.set_authors(
            [__author__])
        about_dialog.set_logo(gtk.gdk.pixbuf_new_from_file(
            "%s/data/imgurup_64.png" % basepath))
        about_dialog.run()
        about_dialog.destroy()

    def clear_fields(self, widget, data=None):
        self.filebtn.unselect_all()
        self.title_entry.set_text("")

    def set_image_title(self, widget, data=None):
        imgname = os.path.basename(self.filebtn.get_filename())
        self.title_entry.set_text(imgname.split('.')[0].title())

    def upload(self, widget, data=None):
        if(self.filebtn.get_filename() == None):
            msgbox = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT,
                                        gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE,
                                        "Nothing to upload, select a file")
            msgbox.set_title("No file selected")
            msgbox.run()
            msgbox.destroy()
        else:
            url = "http://api.imgur.com/2/upload.json"
            imagedata = open(self.filebtn.get_filename()).read()
            values = {"key": config['apikey'],
                "image": imagedata.encode('base64'),
                "title": self.title_entry.get_text()}
            data = urllib.urlencode(values)
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req)
            imagelinks = simplejson.loads(response.read())
            self.store_to_db(imagelinks)
            self.show_info(imagelinks)

    def show_info(self, imagelinks):
        self.dialog = builder.get_object('dialog1')
        close_dialog = builder.get_object('button1')
        close_dialog.connect("clicked", self.close_dialog)
        origentry = builder.get_object('entry1')
        origentry.set_text(imagelinks['upload']['links']['original'])
        imgurentry = builder.get_object('entry2')
        imgurentry.set_text(imagelinks['upload']['links']['imgur_page'])
        imgurentry = builder.get_object('entry3')
        imgurentry.set_text(imagelinks['upload']['links']['delete_page'])
        imgurentry = builder.get_object('entry4')
        imgurentry.set_text(imagelinks['upload']['links']['small_square'])
        imgurentry = builder.get_object('entry5')
        imgurentry.set_text(imagelinks['upload']['links']['large_thumbnail'])
        self.dialog.show()

    def close_dialog(self, widget, data=None):
        self.dialog.hide()

    def show_logview(self, sender, data=None):
        logdialog = gtk.Dialog()
        logdialog.set_icon_from_file("%s/data/imgurup_24.png" % basepath)
        logdialog.set_size_request(600, 300)
        logdialog.set_title("Images log")
        
        
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        logdialog.vbox.pack_start(sw, True, True, 0)

        self.store = self.create_model()

        self.treeView = gtk.TreeView(self.store)
        self.treeView.connect('row-activated', self.on_logrow_active)
        self.treeView.set_rules_hint(True)
        delbutt = gtk.Button(stock=gtk.STOCK_DELETE)
        delbutt.connect('clicked', self.delete_selected_row)
        sw.add(self.treeView)

        self.create_columns(self.treeView)

        logdialog.action_area.pack_start(delbutt)

        logdialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)

        logdialog.show_all()
        response = logdialog.run()
        if response == gtk.RESPONSE_CLOSE:
                logdialog.destroy()
        logdialog.destroy()

    def delete_selected_row(self, button, data=None):
        selection = self.treeView.get_selection()
        model, iter = selection.get_selected()
        try:
            conn = sqlite.connect("%s/data/imgurup.db" % basepath)
            c = conn.cursor()
            c.execute("""DELETE FROM log WHERE delete_link='%s'""" % (model[iter][2]))
            conn.commit()
            c.close()
            webbrowser.open_new(model[iter][2])
            self.store.clear()
            self.treeView.set_model(self.create_model())
        except TypeError:
            print "nothing selected"

    def on_logrow_active(self, widget, row, col):
        model = widget.get_model()
        webbrowser.open_new("%s?tags" % model[row][0])

    def create_model(self):
        store = gtk.ListStore(str, str, str)
        conn = sqlite.connect("%s/data/imgurup.db" % basepath)
        c = conn.cursor()
        c.execute("""SELECT * FROM log""")
        rows = c.fetchall()
        for row in rows:
            store.append([row[1], row[2], row[3]])
        c.close()
        return store

    def create_columns(self, treeView):
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Link:", rendererText, text=0)
        column.set_expand(True)
        column.set_sort_column_id(0)
        treeView.append_column(column)

        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Title:", rendererText, text=1)
        column.set_expand(True)
        column.set_sort_column_id(1)
        treeView.append_column(column)

        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Delete URL", rendererText, text=2)
        column.set_expand(True)
        column.set_sort_column_id(2)
        treeView.append_column(column)
        
    def icon_clicked(self, sender, data=None):
        if(self.windowstate == 0):
            self.window.show_all()
            self.windowstate = 1
        else:
            self.window.hide_on_delete()
            self.windowstate = 0
            return True
            
    def set_api_key(self, widget, data=None):
        apidialog = gtk.Dialog()
        apidialog.set_icon_from_file("%s/data/imgurup_24.png" % basepath)
        apientry = gtk.Entry()
        apientry.set_text(config['apikey'])
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label("API Key:"), False, 5, 5)
        hbox.pack_start(apientry)
        apidialog.vbox.pack_start(gtk.Label("Enter your API Key for Imgur.com"))
        apidialog.vbox.pack_end(hbox, True, True, 0)
        apidialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        apidialog.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        apidialog.show_all()
        response = apidialog.run()
        if response == gtk.RESPONSE_OK:
            config['apikey'] = apientry.get_text()
            config.write()
            apidialog.destroy()
        else:
            apidialog.destroy()
        

    def right_click_event(self, icon, button, time):
        menu = gtk.Menu()

        about = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        logview = gtk.ImageMenuItem(gtk.STOCK_INDEX)
        logview.set_label("Log viewer")
        logview.connect("activate", self.show_logview)
        quit = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        about.connect("activate", self.show_about)
        quit.connect("activate", self.window_destroy)
        apimenu = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        apimenu.set_label("API Key")
        apimenu.connect("activate", self.set_api_key)

        menu.append(about)
        menu.append(logview)
        menu.append(gtk.SeparatorMenuItem())
        menu.append(apimenu)
        menu.append(gtk.SeparatorMenuItem())
        menu.append(quit)
        menu.show_all()

        menu.popup(None, None, gtk.status_icon_position_menu,
                   button, time, self.statusicon)
                   
    def store_to_db(self, imagelinks):
        conn = sqlite.connect("%s/data/imgurup.db" % basepath)
        c = conn.cursor()
        c.execute("""INSERT INTO log(view_link, delete_link, title) VALUES('%s', '%s', '%s')""" % (imagelinks['upload']['links']['imgur_page'], imagelinks['upload']['links']['delete_page'], imagelinks['upload']['image']['title']))
        conn.commit()
        c.close()

class SingleService(dbus.service.Object):
    
    def __init__(self, app):
        self.app = app
        bus_name = dbus.service.BusName('org.imgurup.Single', bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/org/imgurup/Single')
        
    @dbus.service.method(dbus_interface='org.imgurup.Single')
    def show_window(self):
        self.app.window.present()
    

if __name__ == "__main__":
    if dbus.SessionBus().request_name("org.imgurup.Single") != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
        message = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT,
                                        gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE,
                                        "ImgurUp is already running!")
        message.set_title("ImgurUp Running")
        message.run()
        message.destroy()
        method = dbus.SessionBus().get_object("org.imgurup.Single", "/org/imgurup/Single").get_dbus_method("show_window")
        method()
    else:
        app = MainApp()
        service = SingleService(app)
        gtk.main()
