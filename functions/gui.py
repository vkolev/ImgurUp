"""
Gui functionality for the ImgurUp application
"""
import gtk
import simplejson
import urllib2
from imgurlib import ImgurLib

COL_PATH = 0


def quit_msg(msg):
    quitdlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                             gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, None)
    quitdlg.set_markup(msg)
    response = quitdlg.run()
    if response == gtk.RESPONSE_YES:
        quitdlg.destroy()
        return True
    else:
        quitdlg.destroy()
        return False


class AboutDialog(object):

    def __init__(self, path):
        builder = gtk.Builder()
        builder.add_from_file("%s/data/main_window.ui" % path)
        about = builder.get_object('aboutdialog1')
        about.run()
        about.destroy()


def show_info(path, links):
    builder = gtk.Builder()
    builder.add_from_file("%s/data/main_window.ui" % path)
    info = builder.get_object('infodialog')
    imagelinks = simplejson.loads(links)
    title = builder.get_object('entry1')
    title.set_text(imagelinks['images']['image']['title'])
    caption = builder.get_object('entry2')
    caption.set_text(imagelinks['images']['image']['caption'])
    hash = builder.get_object('entry3')
    hash.set_text(imagelinks['images']['image']['hash'])
    deletehash = builder.get_object('entry4')
    deletehash.set_text(imagelinks['images']['image']['deletehash'])
    original = builder.get_object('entry5')
    original.set_text(imagelinks['images']['links']['original'])
    imgur = builder.get_object('entry6')
    imgur.set_text(imagelinks['images']['links']['imgur_page'])
    delete = builder.get_object('entry7')
    delete.set_text(imagelinks['images']['links']['delete_page'])
    small = builder.get_object('entry8')
    small.set_text(imagelinks['images']['links']['small_square'])
    large = builder.get_object('entry9')
    large.set_text(imagelinks['images']['links']['large_thumbnail'])
    info.add_buttons(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE, gtk.STOCK_SAVE, gtk.RESPONSE_OK)
    response = info.run()
    if response == gtk.RESPONSE_OK:
        info.destroy()
        return True
    info.destroy()


class AlbumsDialog(object):

    def __init__(self, path, il):
        self.il = il
        self.path = path
        builder = gtk.Builder()
        builder.add_from_file('%s/data/main_window.ui' % path)
        newalbum = builder.get_object('button7')
        newalbum.connect('clicked', self.create_album)
        delalbum = builder.get_object('button5')
        delalbum.connect('clicked', self.delete_album)
        info_string = builder.get_object('label42')
        image_count = self.il.get_account_album_count('me')
        info_string.set_markup("You have <b>%s</b> albums." %
                               image_count)

        self.album_store = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        self.album_list = builder.get_object('treeview1')
        self.album_list.set_model(self.album_store)
        self.album_list.connect('row-activated', self.get_album)
        self.create_album_columns(self.album_list)
        self.album_store.append([self.album_list.render_icon(gtk.STOCK_HOME, size=gtk.ICON_SIZE_MENU, detail=None), 'Unsorted', ""])
        try:
            albums = self.il.get_account_albums('me')
            for album in albums:
                self.album_store.append([self.album_list.render_icon(gtk.STOCK_DIRECTORY, size=gtk.ICON_SIZE_MENU, detail=None), album.title, album.id])
        except:
            pass

        self.icon_sw = builder.get_object('scrolledwindow2')
        self.icon_store = self.create_store()
        self.fillstore()
        self.icon_list = gtk.IconView(self.icon_store)
        self.icon_list.set_pixbuf_column(1)
        self.icon_list.grab_focus()
        self.icon_sw.add(self.icon_list)
        self.icon_list.show()
        #self.icon_list.connect('item-activated', self.show_image_info)
        self.icon_list.connect('button-press-event', self.image_menu)
        self.albumdialog = builder.get_object('albumdialog')
        self.albumdialog.set_title("All Images")
        self.albumdialog.add_buttons(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        response = self.albumdialog.run()
        if response == gtk.RESPONSE_CLOSE:
            self.albumdialog.destroy()
        self.albumdialog.destroy()

    def show_image_info(self, tree, path):
        model = self.icon_list.get_model()
        ImageInfo(self.path, self.il, model[path][0])

    def image_menu(self, widget, event):
        if event.button == 3:
            menu = gtk.Menu()
            show_info = gtk.ImageMenuItem(gtk.STOCK_INFO)
            show_info.connect("activate", self.show_image_info,
                               self.icon_list.get_path_at_pos(int(event.x),
                                                              int(event.y)))
            del_option = gtk.ImageMenuItem(gtk.STOCK_DELETE)
            del_option.connect("activate", self.delete_image,
                               self.icon_list.get_path_at_pos(int(event.x),
                                                              int(event.y)))
            menu.append(show_info)
            menu.append(del_option)
            menu.popup(None, None, None, 1, 0)
            menu.show_all()

    def delete_image(self, sender, path):
        model = self.icon_list.get_model()
        image = simplejson.loads(self.il.get_image_info(model[path][0]))['images']['image']
        confirm = gtk.MessageDialog(None, gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                             gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, None)
        confirm.set_markup("You are about to delete image: <b>%s</b>\n\nAre you sure" % image['title'])
        if confirm.run() == gtk.RESPONSE_YES:
            response = self.il.delete_image(image['deletehash'])
            print response
            if "Success" in response:
                self.icon_store.remove(model.get_iter(path))
        confirm.destroy()

    def get_album(self, tree, path, column):
        model = tree.get_model()
        self.fillstore(model[path][2])

    def delete_album(self, sender):
        selection = self.album_list.get_selection()
        if selection.count_selected_rows() > 0:
            (tm, ti) = selection.get_selected()
            albumhash = tm.get_value(ti, 2)
            confirm = gtk.MessageDialog(None, gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                             gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, None)
            confirm.set_markup("You are going to delete the album <b>%s</b>.\n\nContinue?" %
                               (tm.get_value(ti, 1)))
            if confirm.run() == gtk.RESPONSE_YES:
                resp = self.il.delete_album(albumhash)
                if "Success" in resp:
                    self.album_store.remove(ti)
            confirm.destroy()
        else:
            pass

    def create_album(self, widget, data=None):
        builder = gtk.Builder()
        builder.add_from_file("%s/data/main_window.ui" % self.path)
        newalbum = builder.get_object('newalbum')
        newalbum.add_buttons(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE,
                             gtk.STOCK_ADD, gtk.RESPONSE_ACCEPT)
        title = builder.get_object('entry10')
        description = builder.get_object('entry11')
        hbox = builder.get_object('hbox13')
        privacy = gtk.combo_box_new_text()
        privacy.append_text('public')
        privacy.append_text('hidden')
        privacy.append_text('secret')
        privacy.show()
        hbox.pack_start(privacy)
        response = newalbum.run()
        if response == gtk.RESPONSE_ACCEPT:
            try:
                response = self.il.create_album(title.get_text(),
                                                description.get_text(),
                                                privacy.get_active_text())
                album = simplejson.loads(response)
                print album['albums']['title']
                self.album_store.append([self.album_list.render_icon(gtk.STOCK_DIRECTORY, size=gtk.ICON_SIZE_MENU, detail=None),
                                             album['albums']['title'], album['albums']['id']])
            except:
                pass
        newalbum.destroy()

    def create_album_columns(self, album_list):
        rendererPixbuf = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn("#", rendererPixbuf)
        column.add_attribute(rendererPixbuf, 'pixbuf', 0)
        album_list.append_column(column)

        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Title", rendererText, text=1)
        album_list.append_column(column)

        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Hash", rendererText, text=2)
        album_list.append_column(column)

    def fillstore(self, albumid=""):
        self.icon_store.clear()
        if albumid == "":
            images = self.il.get_account_images('me')
            for image in images:
                name = image.id
                response = urllib2.urlopen("http://i.imgur.com/%ss.jpg" % image.id)
                loader = gtk.gdk.PixbufLoader()
                loader.write(response.read())
                loader.close()
                img = loader.get_pixbuf()
                self.icon_store.append([name, img])
        else:
            images = self.il.get_album_images(albumid)
            for image in images:
                name = image.id
                response = urllib2.urlopen("http://i.imgur.com/%ss.jpg" % image.id)
                loader = gtk.gdk.PixbufLoader()
                loader.write(response.read())
                loader.close()
                img = loader.get_pixbuf()
                self.icon_store.append([name, img])

    def create_store(self):
        store = gtk.ListStore(str, gtk.gdk.Pixbuf)
        store.set_sort_column_id(COL_PATH, gtk.SORT_ASCENDING)
        return store


class ImageInfo(object):

    def __init__(self, path, il, hash):
        self.path = path
        self.il = il
        builder = gtk.Builder()
        builder.add_from_file('%s/data/main_window.ui' % self.path)
        imageview = builder.get_object('imageview')
        img = self.il.get_image(hash)
        image = builder.get_object('image5')
        response = urllib2.urlopen("http://i.imgur.com/%sm.jpg" % img.id)
        loader = gtk.gdk.PixbufLoader()
        loader.write(response.read())
        loader.close()
        image.set_from_pixbuf(loader.get_pixbuf())
        imageview.add_buttons(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)

        #============= entries ================
        title = builder.get_object('label29')
        titl_string = img.title
        if titl_string == None:
            title.set_text("None")
        else:
            title.set_text(titl_string)
        desc = builder.get_object('label31')
        desc_string = img.description
        if desc_string == None:
            desc.set_text("None")
        else:
            desc.set_text(desc_string)
        orig = builder.get_object('entry12')
        orig.set_text(img.link)
        imgur = builder.get_object('entry13')
        imgur.set_text("http://imgur.com/%s" % img.id)
        square = builder.get_object('entry14')
        square.set_text("http://i.imgur.com/%ss.jpg" % img.id)
        thumb = builder.get_object('entry15')
        thumb.set_text("http://i.imgur.com/%sl.jpg" % img.id)
        delete = builder.get_object('entry18')
        delete.set_text(img.deletehash)
        forum = builder.get_object('entry16')
        #links = self.il.generate_links(img.id)
        #forum.set_text()
        #html = builder.get_object('entry17')
        #html.set_text(links['html'])

        response = imageview.run()
        if response == gtk.RESPONSE_CLOSE:
            imageview.destroy()
        imageview.destroy()


class PrefsDialog(object):

    def __init__(self, path, config):
        builder = gtk.Builder()
        builder.add_from_file("%s/data/main_window.ui" % path)
        dialog = builder.get_object('prefdialog')
        self.img_entry = builder.get_object('entry19')
        self.img_entry.set_text(config['screenshotname'])
        self.path_entry = builder.get_object('entry20')
        self.path_entry.set_text(config['screenshotpath'])
        open_dir = builder.get_object('button4')
        open_dir.connect("clicked", self.select_shot_dir)
        self.capt_remove = builder.get_object('checkbutton1')
        self.capt_remove.set_active(bool(config['captionremove']))
        self.shot_timeout = builder.get_object('spinbutton1')
        self.shot_timeout.set_value(int(config['waitscreen']))
        dialog.add_buttons(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        dialog.add_buttons(gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        if dialog.run() == gtk.RESPONSE_OK:
            config['screenshotname'] = self.img_entry.get_text()
            config['screenshotpath'] = self.path_entry.get_text()
            config['captionremove'] = int(self.capt_remove.get_active())
            config['waitscreen'] = int(self.shot_timeout.get_value())
            config.write()
        dialog.destroy()

    def select_shot_dir(self, sender):
        opendialog = gtk.FileChooserDialog("Select output folder",
                                           None,
                                           gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                           (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                            gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        if opendialog.run() == gtk.RESPONSE_OK:
            self.path_entry.set_text(opendialog.get_filename())
        opendialog.destroy()
