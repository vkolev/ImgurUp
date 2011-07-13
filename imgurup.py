#!/usr/bin/env python2.6
#-*- encoding: utf-8 -*-

import os
import sys
import mimetypes
import dbus
import dbus.service
import dbus.glib
import simplejson
import time
import gobject

basepath = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]))) 

try:
    import pygtk
    pygtk.require("2.0")
except:
    pass

try:
    import gtk
except:
    print "You need GTK installed to use this application"
    
from configobj import ConfigObj
from functions.gui import *
from functions.imgurlib import ImgurLib
config = ConfigObj("%s/data/config.ini" % basepath)

dnd_list = [ ( 'text/uri-list', 0, 80 ) ]


class ImgurUp(object):
    
    def __init__(self):
        self.work_left = True
        builder = gtk.Builder()
        builder.add_from_file('%s/data/main_window.ui' % basepath)
        builder.connect_signals(self)
        self.windowstate = 1
        self.user_auth = 0
        self.imagepath = builder.get_object('imagepath')
        self.imagetitle = builder.get_object('imagetitle')
        self.imagecaption = builder.get_object('imagecaption')
        self.image = builder.get_object('imagepreview')
        self.filefilter = builder.get_object('filefilter1')
        self.filefilter.set_name("Image Files")
        self.filefilter.add_pixbuf_formats()
        self.menu1 = builder.get_object('menu1')
        self.window = builder.get_object('window1')
        self.text_info = builder.get_object('label39')
        self.statusicon = gtk.StatusIcon()
        self.statusicon.set_from_file('%s/data/imgurup.svg' % basepath)
        self.statusicon.connect("popup-menu", self.right_click_event)
        self.statusicon.connect("activate", self.icon_clicked)
        self.statusicon.set_tooltip("Imgur Uploader")
        self.window.connect("drag_data_received", self.on_file_dragged)
        self.window.drag_dest_set(gtk.DEST_DEFAULT_MOTION | gtk.DEST_DEFAULT_DROP,
                                 dnd_list, gtk.gdk.ACTION_COPY)
        self.window.show_all()
        if int(config['workmode']) == 0:
            self.albums = builder.get_object('albumbutton')
            self.albums.set_sensitive(False)
            self.user = builder.get_object('authorbutton')
            self.user.set_sensitive(False)
        else:
            self.il = ImgurLib(config['imgurkey'], config['imgursecret'])
            if config['usertoken'] and config['usersecret']:
                self.il.authorize_with_token(config['usertoken'], config['usersecret'])
                self.user_auth = 1
            else:
                self.user_info()
                
    def exit(self, widget=None):
        if quit_msg("<b>Are you sure to quit?</b>") == True:
            gtk.main_quit()
        else:
            return False
        
    def on_window1_destroy(self, widget, data=None):
        self.window.hide_on_delete()
        self.windowstate = 0
        return True
        
    def select_image(self, widget, data=None):
        filedlg = gtk.FileChooserDialog("Select image file...", None,
                      gtk.FILE_CHOOSER_ACTION_OPEN,
                      (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                      gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        filedlg.add_filter(self.filefilter)
        response = filedlg.run()
        if response == gtk.RESPONSE_OK:
            self.imagepath.set_text(filedlg.get_filename())
            imgname = os.path.basename(filedlg.get_filename())
            pixbuf = gtk.gdk.pixbuf_new_from_file(filedlg.get_filename())
            self.image.set_from_pixbuf(pixbuf.scale_simple(300, 200, gtk.gdk.INTERP_NEAREST))
            self.imagetitle.set_text(imgname.split('.')[0].title())
        else:
            filedlg.destroy()
        filedlg.destroy()
        
    def upload_image(self, widget, data=None):
        if self.check_fields() == True:
            self.text_info.set_markup("<b><i>Uploading...</i></b>")
            info = self.il.upload_image(self.imagepath.get_text(),
                                 self.imagetitle.get_text(),
                                 self.imagecaption.get_text())
            if show_info(basepath, info) == True:
                f = open('%s/recent.txt' % basepath, 'a')
                f.write(info+"\n\r")
                f.close()
                menuItem = gtk.MenuItem(simplejson.loads(info)['images']['image']['title'])
                menuItem.connect('activate', lambda term: show_info(basepath, info))
                self.menu1.append(menuItem)
                self.menu1.show_all()
            self.text_info.set_text("")
    
    def check_fields(self):
        if not self.imagepath.get_text():
            return False
        elif not self.imagecaption.get_text():
            self.imagecaption.set_text("None")
        else:
            return True
        
    def clear_fields(self, widget, data=None):
        self.imagetitle.set_text("")
        self.imagepath.set_text("")
        self.imagecaption.set_text("")
        self.image.set_from_file("%s/data/imgurup-logo.png" % basepath)
        
    def take_screenshot(self, widget, data=None):
        if config['screenshotpath'] != "":
            path = config['screenshotpath']
        else:
            path = os.getenv("HOME")
        if self.windowstate == 1:
            self.window.hide()
            self.windowstate = 0
            shot = self.fullscreen_shot(path)
            uploadfile = path+"/"+shot
            self.window.show_all()
            self.windowstate = 1
        else:
            shot = self.fullscreen_shot(path)
            self.window.show_all()
            self.windowstate = 1
        self.imagepath.set_text(path+"/"+shot)
        pixbuf = gtk.gdk.pixbuf_new_from_file(path+"/"+shot)
        self.image.set_from_pixbuf(pixbuf.scale_simple(300, 200, gtk.gdk.INTERP_NEAREST))
        self.imagetitle.set_text(shot.split('.')[0].title())
        if bool(config['captionremove']) == False:
            self.imagecaption.set_text("Desktop Screenshot with ImgurUp")
            
    
    def fullscreen_shot(self, path = os.getenv('HOME')):
        from string import Template
        imgformat = "png"
        width = gtk.gdk.screen_width()
        height = gtk.gdk.screen_height()
        s = Template(config['screenshotname'])
        shotname = s.safe_substitute(date = time.strftime("%Y%m%d%H%M%S", time.localtime()),
                     time = time.strftime("H%M%S", time.localtime()),
                     count = config['count'])
        time.sleep(float(config['waitscreen']))
        screenshot = gtk.gdk.Pixbuf.get_from_drawable(
                    gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, width, height),
                    gtk.gdk.get_default_root_window(),
                    gtk.gdk.colormap_get_system(),
                    0, 0, 0, 0, width, height)
        screenshot.save(path+"/"+shotname+"."+imgformat, imgformat)
        config['count'] = int(config['count']) + 1
        config.write()
        return shotname+"."+imgformat
    
    def show_albums(self, widget, data=None):
        AlbumsDialog(basepath, self.il)
    
    def about_click(self, widget, data=None):
        AboutDialog(basepath)
    
    def on_file_dragged(self, widget, context, x, y, select, target, timestamp):
        imagepath = "/" + select.data.strip('\r\n\x00').strip("file://")
        if mimetypes.guess_type(imagepath)[0].startswith('image') == True:
            self.imagepath.set_text(imagepath)
            imagename = os.path.basename(imagepath)
            pixbuf = gtk.gdk.pixbuf_new_from_file(imagepath)
            self.image.set_from_pixbuf(pixbuf.scale_simple(300, 200, gtk.gdk.INTERP_NEAREST))
            self.imagetitle.set_text(imagename.split('.')[0].title())
        else:
            pass
        
    def user_info(self, sender=None, data=None):
        builder = gtk.Builder()
        builder.add_from_file('%s/data/main_window.ui' % basepath)
        userinfo = builder.get_object('userdialog')
        authimage = builder.get_object('image1')
        authtext = builder.get_object('label15')
        username = builder.get_object('label19')
        prof = builder.get_object('label18')
        privacy = builder.get_object('label21')
        credits = builder.get_object('label23')
        authbut = builder.get_object('button3')
        if self.user_auth == 1:
            info = simplejson.loads(self.il.account_info())
            authimage.set_from_stock(gtk.STOCK_OK, gtk.ICON_SIZE_SMALL_TOOLBAR)
            authtext.set_markup('<span foreground="green">Authenticated</span>')
            username.set_text(info['account']['url'])
            prof.set_text(info['account']['is_pro'])
            privacy.set_text(info['account']['default_album_privacy'])
            info = simplejson.loads(self.il.get_credits())
            credits.set_markup('<b>%s</b> credits left' % info['credits']['remaining'])
            authbut.set_sensitive(False)
        else:
            authbut.connect("clicked", self.authenticate)
        
        userinfo.add_buttons(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        userinfo.run()
        userinfo.destroy()
        
    def authenticate(self, widget=None, data=None):
        authdialog = gtk.Dialog("Authenticate", None, gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                                      (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                       gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        link = gtk.LinkButton(self.il.get_auth_url(), "Click here...")
        label = gtk.Label("Visit the following Link and paste the PIN code")
        entry = gtk.Entry()
        authdialog.vbox.pack_start(label)
        authdialog.vbox.pack_start(link)
        authdialog.vbox.pack_start(entry)
        authdialog.show_all()
        
        response = authdialog.run()
        print response
        if response == gtk.RESPONSE_ACCEPT:
            if self.il.authorize(entry.get_text()):
                self.user_auth = 1
                config['usertoken'] = self.il.oauth_token
                config['usersecret'] = self.il.oauth_token_secret
                config.write()
            else:
                error_msg("The PIN was not correct")
                authdialog.destroy()
        authdialog.destroy()
            
    def open_preferences(self, sender, data=None):
        PrefsDialog(basepath, config)
        
    def icon_clicked(self, sender, data=None):
        if(self.windowstate == 0):
            self.window.show_all()
            self.windowstate = 1
        else:
            self.window.hide_on_delete()
            self.windowstate = 0
            return True
        
    def right_click_event(self, icon, button, time):
        menu = gtk.Menu()

        about = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        logview = gtk.ImageMenuItem()
        logview.set_image(gtk.image_new_from_icon_name('emblem-photos', gtk.ICON_SIZE_MENU))
        logview.set_label("Account Albums")
        logview.connect("activate", self.show_albums)
        quit = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        about.connect("activate", self.about_click)
        quit.connect("activate", self.exit)
        apimenu = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        apimenu.set_label("Preferences")
        apimenu.connect("activate", self.open_preferences)
        shotmenu = gtk.ImageMenuItem(gtk.STOCK_FULLSCREEN)
        shotmenu.set_label("Take Screenshot")
        shotmenu.connect("activate", self.take_screenshot)

        menu.append(about)
        menu.append(logview)
        menu.append(gtk.SeparatorMenuItem())
        menu.append(shotmenu)
        menu.append(gtk.SeparatorMenuItem())
        menu.append(apimenu)
        menu.append(gtk.SeparatorMenuItem())
        menu.append(quit)
        menu.show_all()

        menu.popup(None, None, gtk.status_icon_position_menu,
                   button, time, self.statusicon)
            
class SingleService(dbus.service.Object):
    
    def __init__(self, app):
        self.app = app
        bus_name = dbus.service.BusName('org.imgurup.Single', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/org/imgurup/Single')
        
    @dbus.service.method(dbus_interface='org.imgurup.Single')
    def show_window(self):
        self.app.window.present()
        
if __name__ == "__main__":
    owner = dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER
    if dbus.SessionBus().request_name("org.imgurup.Single") != owner:
        message = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT,
                                        gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE,
                                        "ImgurUp is already running!")
        message.set_title("ImgurUp Running")
        message.run()
        message.destroy()
        method = dbus.SessionBus().get_object("org.imgurup.Single", 
            "/org/imgurup/Single").get_dbus_method("show_window")
        method()
    else:
        app = ImgurUp()
        service = SingleService(app)
        gtk.main()
        
        
