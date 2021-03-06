#!/usr/bin/python
# -*- coding: utf-8 -*-

#	Copyright (C) 2009 Daniel Fett
# 	Source inspired by Jesper Vestergaard's MokoCaching
# 	This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#	Author: Daniel Fett simplecaching@fragcom.de
#


### For the html data download and login class

### For the gui :-)
import gtk
import gobject
import pango

### For loading gps values
import socket
#import gpsthreads
import re

### For loading the conf file
import ConfigParser
import os

#import cProfile
#import pstats

import math


class Coordinate():
	re_to_dm_array = re.compile('^(\d?)(\d)(\d) (\d)(\d)\.(\d)(\d)(\d)$')
	re_to_d_array = re.compile('^(\d?)(\d)(\d).(\d)(\d)(\d)(\d)(\d)$')
	
	def __init__(self, lat, lon, name = "No Name"):
		self.lat = lat
		self.lon = lon
		self.name = name
		
	def from_d(self, lat, lon):
		self.lat = lat
		self.lon = lon
		
	def from_dm(self, latdd, latmm, londd, lonmm):
		self.lat = latdd + (latmm/60)
		self.lon = londd + (lonmm/60)
		
	def from_dm_array(self, sign_lat, lat, sign_lon, lon):
		self.from_dm(sign_lat * (lat[0]*10 + lat[1]),
			float(str(lat[2]) + str(lat[3]) + "." + str(lat[4]) + str(lat[5]) + str(lat[6])),
			sign_lon * (lon[0] * 100 + lon[1] * 10 + lon[2]),
			float(str(lon[3]) + str(lon[4]) + "." + str(lon[5]) + str(lon[6]) + str(lon[7])))

	def from_d_array(self, sign_lat, lat, sign_lon, lon):
		self.lat = int(sign_lat) * float("%d%d.%d%d%d%d%d" % tuple(lat))
		self.lon = int(sign_lon) * float("%d%d%d.%d%d%d%d%d" % tuple(lon))
			
	def to_dm_array(self):
		[[lat_d, lat_m],[lon_d, lon_m]] = self.to_dm()
		
		d_lat = self.re_to_dm_array.search("%02d %06.3f" % (abs(lat_d), abs(lat_m)))
		d_lon = self.re_to_dm_array.search("%03d %06.3f" % (abs(lon_d), abs(lon_m)))
		return [
			[d_lat.group(i) for i in range (2, 9)],
			[d_lon.group(i) for i in range (1, 9)]
			]

	def to_d_array(self):

		d_lat = self.re_to_d_array.search("%08.5f" % abs(self.lat))
		d_lon = self.re_to_d_array.search("%09.5f" % abs(self.lon))
		return [
			[d_lat.group(i) for i in range (2, 7)],
			[d_lon.group(i) for i in range (1, 7)]
			]
		
	def to_dm(self):
		return [ [int(math.floor(self.lat)), (self.lat - math.floor(self.lat)) * 60] ,
			[int(math.floor(self.lon)), (self.lon - math.floor(self.lon)) * 60] ]
	
	def bearing_to(self, target):
		lat1 = math.radians(self.lat)
		lat2 = math.radians(target.lat)
		lon1 = math.radians(self.lon)
		lon2 = math.radians(target.lon)
		
		dlon = math.radians(target.lon - self.lon);
		y = math.sin(dlon) * math.cos(lat2)
		x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(dlon)
		bearing = math.degrees(math.atan2(y, x))
		
		return (360 + bearing) % 360

	def get_lat(self, format):
		l = abs(self.lat)
		if self.lat > 0:
			c = 'N'
		else:
			c = 'S'
		if format == Gui.FORMAT_D:
			return "%s%8.5f°" % (c, l)
		elif format == Gui.FORMAT_DM:
			return "%s%2d° %06.3f'" % (c, math.floor(l), (l - math.floor(l)) * 60)

	def get_lon(self, format):
		l = abs(self.lon)
		if self.lon > 0:
			c = 'E'
		else:
			c = 'W'
		if format == Gui.FORMAT_D:
			return "%s%9.5f°" % (c, l)
		elif format == Gui.FORMAT_DM:
			return "%s%3d° %06.3f'" % (c, math.floor(l), (l - math.floor(l)) * 60)

	def distance_to (self, target):
		R = 6371000;
		dlat = math.pow(math.sin(math.radians(target.lat-self.lat)/2),2)
		dlon = math.pow(math.sin(math.radians(target.lon-self.lon)/2),2) 
		a = dlat + math.cos(math.radians(self.lat)) * math.cos(math.radians(target.lat)) * dlon; 
		c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)); 
		return R * c;
		
		
		
class Updown():
	def __init__(self, table, position, small):
		self.value = int(0)
		self.label = gtk.Label("0")
		self.button_up = gtk.Button("+")
		self.button_down = gtk.Button("-")
		table.attach(self.button_up, position, position + 1, 0, 1)
		table.attach(self.label, position, position + 1, 1, 2)
		table.attach(self.button_down, position, position + 1, 2, 3)
		self.button_up.connect('clicked', self.value_up)
		self.button_down.connect('clicked', self.value_down)
		if small:
			font = pango.FontDescription("sans 8")
		else:
			font = pango.FontDescription("sans 12")
		self.label.modify_font(font)
		self.button_up.child.modify_font(font)
		self.button_down.child.modify_font(font)
	
	def value_up(self, target):
		self.value = int((self.value + 1) % 10)
		self.update()
	
	def value_down(self, target):
		self.value = int((self.value - 1) % 10)
		self.update()
		
	def set_value(self, value):
		self.value = int(value)
		self.update()
		
	def update(self):
		self.label.set_text(str(self.value))
		

		
class PlusMinusUpdown():
	def __init__(self, table, position, labels):
		self.is_neg = False
		self.labels = labels
		self.button = gtk.Button(labels[0])
		table.attach(self.button, position, position + 1, 1, 2)
		self.button.connect('clicked', self.value_toggle)
		self.button.child.modify_font(pango.FontDescription("sans 8"))
	
	def value_toggle(self, target):
		self.is_neg = not self.is_neg
		self.update()
		
	def set_value(self, value):
		self.is_neg = (value < 0)
		self.update()
		
	def get_value(self):
		if self.is_neg:
			return -1
		else:
			return 1
		
	def update(self):
		if self.is_neg:
			text = self.labels[0]
		else:
			text = self.labels[1]
		self.button.child.set_text(text)

class Updown_Rows():
	def __init__(self, format, coord):
		self.format = format
		if format == Gui.FORMAT_DM:
			[init_lat, init_lon] = coord.to_dm_array()
		elif format == Gui.FORMAT_D:
			[init_lat, init_lon] = coord.to_d_array()
		[self.table_lat, self.chooser_lat] = self.generate_table(False, init_lat)
		[self.table_lon, self.chooser_lon] = self.generate_table(True, init_lon)
		self.switcher_lat.set_value(coord.lat)
		self.switcher_lon.set_value(coord.lon)

	def get_value(self):
		coord = Coordinate(0,0)
		lat_values = [ud.value for ud in self.chooser_lat]
		lon_values = [ud.value for ud in self.chooser_lon]
		if self.format == Gui.FORMAT_DM:
			coord.from_dm_array(self.switcher_lat.get_value(), lat_values, self.switcher_lon.get_value(), lon_values)
		elif self.format == Gui.FORMAT_D:
			coord.from_d_array(self.switcher_lat.get_value(), lat_values, self.switcher_lon.get_value(), lon_values)
		return coord

	def generate_table(self, is_long, initial_value):
		interrupt = {}
		if self.format == Gui.FORMAT_DM and not is_long:
			small = 2
			num = 7
			interrupt[3] =  "°"
			interrupt[6] = "."
		elif self.format == Gui.FORMAT_DM and is_long:
			small = 3
			num = 8
			interrupt[4] = "°"
			interrupt[7] = "."
		elif self.format == Gui.FORMAT_D and not is_long:
			small = 2
			num = 7
			interrupt[3] = "."
		elif self.format == Gui.FORMAT_D and is_long:
			small = 3
			num = 8
			interrupt[4] = "."

		table = gtk.Table(3, num + len(interrupt) + 1, False)
		
		if is_long:
			self.switcher_lon = PlusMinusUpdown(table, 0, ['W', 'E'])
		else:
			self.switcher_lat = PlusMinusUpdown(table, 0, ['S', 'N'])
		
		chooser = []
		cn = 0
		for i in range(1, num + len(interrupt) + 1):
			if i in interrupt:
				table.attach(gtk.Label(interrupt[i]), i, i+1, 1, 2)
			else:
				ud = Updown(table, i, cn < small)
				if cn < len(initial_value):
					ud.set_value(initial_value[cn])
				chooser.append(ud)
				cn = cn + 1

		return [table, chooser]
		
class StoredTargetDisplay():
	def __init__(self, coord, radio_group, gui):
		self.gui = gui
		
		self.radio_button = gtk.RadioButton(radio_group, "")
		self.coord_display = self.radio_button.child
		self.name_input = gtk.Entry()
		
		self.coord = coord
		self.update()
		self.name_input.connect('changed', self.put_name)
		self.name_input.connect('focus-in-event', self.put_name)
		self.temp_name = ""
		
	def put_name(self, target, blub = None):
		self.radio_button.set_active(True)
		if self.coord == None:
			self.temp_name = self.name_input.get_text()
		else:
			self.coord.name = self.name_input.get_text()
	
	def update(self):
		if self.coord == None:
			self.name_input.set_text("")
			self.coord_display.set_text("-")
		else:
			self.name_input.set_text(self.coord.name)
			self.coord_display.set_text("%s\n%s" % (self.coord.get_lat(self.gui.format), self.coord.get_lon(self.gui.format)))
	
	def edit(self):
		if self.coord == None:
			c = self.gui.gps_position
			c.name = self.temp_name
		else:
			c = self.coord
		self.coord = self.gui.show_coordinate_input(c)
		self.update()	
		
	def set_coord(self, coord):
		temp_name = coord
		self.coord = coord
		self.coord = temp_name
		self.update()	
		

class StoredTargetDialog():
	def __init__(self, gui):
		self.gui = gui
		global dialog
		dialog = gtk.Dialog("Load/Store", None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
		
	
		self.table = gtk.Table(1,1,False)
		
		self.frame = gtk.Frame("Stored Targets")
		self.frame.add(self.table)
		dialog.vbox.pack_start(self.frame)
		table = gtk.Table(4, 1, False)
		
		buttonDelete = gtk.Button(stock = "gtk-remove")
		buttonDelete.get_children()[0].get_children()[0].get_children()[1].set_text("")
		table.attach(buttonDelete, 0, 1, 0, 1)
		buttonDelete.connect('clicked', self.stored_target_callback, "delete")
		
		buttonSetCurrent = gtk.Button(stock = "gtk-convert")
		buttonSetCurrent.get_children()[0].get_children()[0].get_children()[1].set_text("")
		table.attach(buttonSetCurrent, 1, 2, 0, 1)
		buttonSetCurrent.connect('clicked', self.stored_target_callback, "store")

		buttonEdit = gtk.Button(stock = "gtk-edit")
		buttonEdit.get_children()[0].get_children()[0].get_children()[1].set_text("")
		table.attach(buttonEdit, 2, 3, 0, 1)
		buttonEdit.connect('clicked', self.stored_target_callback, "edit")
		
		buttonUse = gtk.Button(stock = "gtk-apply")
		buttonUse.get_children()[0].get_children()[0].get_children()[1].set_text("")
		table.attach(buttonUse, 3, 4, 0, 1)
		buttonUse.connect('clicked', self.stored_target_callback, "use")
		table.set_size_request(-1, 40)
		dialog.vbox.pack_start(table)
		
	def run(self, nothing):
		self.rebuild()
		dialog.run()
		self.gui.write_config()
		dialog.hide()
		self.update_stored_targets()
		self.gui.write_config()
		
	def update_stored_targets(self):	
		self.gui.stored_targets = []	
		for i in self.stored_inputs:
			if i.coord != None:
				self.gui.stored_targets.append(i.coord)
				
	def rebuild(self, activate = -1):		
		self.frame.remove(self.table)
		self.table = self.build_table(activate)
		self.frame.add(self.table)
		dialog.show_all()
		
	def build_table(self, activate = -1):
		table = gtk.Table(2, len(self.gui.stored_targets)+1, False)
		self.stored_inputs = []
		group = None
		for i in range(len(self.gui.stored_targets) + 1):
			if i < len(self.gui.stored_targets):
				std = StoredTargetDisplay(self.gui.stored_targets[i], group, self.gui)
			else:
				std = StoredTargetDisplay(None, group, self.gui)
			if i == activate:
				std.radio_button.set_active(True)
			if group == None:
				group = std.radio_button
			table.attach(std.radio_button, 0, 1, i, i+1)
			table.attach(std.name_input, 1, 2, i, i+1)
			self.stored_inputs.append(std)
		return table
		
	def stored_target_callback(self, target, action):
		current = None
		num = 0
		for i in self.stored_inputs:
			if i.radio_button.get_active():
				current = i
				active = num
			num = num + 1
		if current == None:
			return
		
		if action == "use":
			if current.coord != None:
				self.gui.target_position = current.coord
				self.gui.update_target_display()
				self.update_stored_targets()
				self.gui.write_config()
				dialog.hide()
		elif action == "edit":
			current.edit()
			self.update_stored_targets()
			self.rebuild(active)
		elif action == "store":
			current.set_coord(self.gui.target_position)
			self.update_stored_targets()
			self.rebuild(active)
		elif action == "delete":
			current.set_coord(None)
			self.update_stored_targets()
			self.rebuild(active)

class Gui():
	FORMAT_D = 0
	FORMAT_DM = 1
    
	def __init__(self):
		# Setting up some variables
		self.drawing_area_configured = False
		self.status = "?"
		self.has_fix = False
		self.format = self.FORMAT_DM
		self.gps_position = Coordinate(0, 0)
		self.target_position = Coordinate(0, 0)
		self.target_distance = 6000
		self.gps_bearing = 0.0
		self.gps_altitude = 0.0
		self.gps_speed = 0.0
		self.gps_sats = 0
		self.stored_targets = []
		global arrow_transformed
		global last_display_data
		global last_arrow_bounds
		arrow_transformed = None
		last_display_data = None
		last_arrow_bounds = None
		
		
		# Dialogs
		self.stored_dialog = StoredTargetDialog(self)
		
		# Main Screen turn on		
		self.window = gtk.Window()
		self.window.connect ("destroy", self.destroy)
		self.window.set_title('Simple Geocaching Tool for Linux')

		table = gtk.Table(6, 3, False)
		self.window.add(table)
		
		global labelLatLon
		labelLatLon = gtk.Label("?")
		table.attach(labelLatLon, 0, 3 ,3 ,4)
		
		global labelTargetLatLon
		labelTargetLatLon = gtk.Label("-")
		table.attach(labelTargetLatLon, 0, 3 ,4 ,5)
		
		global progressbar
		progressbar = gtk.ProgressBar()
		progressbar.set_text("")
		table.attach(progressbar, 0, 3, 0, 1)

		global labelAltitude
		labelAltitude = gtk.Label("ALT")
		table.attach(labelAltitude, 0, 1, 1, 2)

		global labelDist
		labelDist = gtk.Label("DIST")
		table.attach(labelDist, 1, 2, 1, 2)

		global labelBearing
		labelBearing = gtk.Label("BEARNG")
		table.attach(labelBearing, 2, 3, 1, 2)
		
		buttonChange = gtk.Button("change")
		table.attach(buttonChange, 2, 3, 5, 6)
		buttonChange.connect('clicked', self.input_target)

		buttonSwitch = gtk.Button("dm/d")
		table.attach(buttonSwitch, 1, 2, 5, 6)
		buttonSwitch.connect('clicked', self.switch_display)
		
		buttonLoadStore = gtk.Button("load/\nstore")
		table.attach(buttonLoadStore, 0, 1, 5, 6)
		buttonLoadStore.connect('clicked', self.stored_dialog.run)
		
		font_big = pango.FontDescription("sans 10")
		font_medium = pango.FontDescription("sans 8")
		font_small = pango.FontDescription("sans 5")
		labelDist.modify_font(font_big)
		labelBearing.modify_font(font_medium)
		labelAltitude.modify_font(font_medium)
		buttonChange.child.modify_font(font_big)
		buttonSwitch.child.modify_font(font_big)
		buttonLoadStore.child.modify_font(font_small)
		
		global drawing_area
		drawing_area = gtk.DrawingArea()
		drawing_area.set_size_request(470, 380)
		drawing_area.show()
		drawing_area.connect("expose_event", self.expose_event)
		drawing_area.connect("configure_event", self.configure_event)
		drawing_area.set_events(gtk.gdk.EXPOSURE_MASK)
		table.attach(drawing_area, 0,3, 2, 3)
		self.window.show_all()	
		self.read_config()
		#self.update_display()
		self.update_target_display()
		self.gps_thread = Gps_reader(self)
		gobject.timeout_add(500, self.read_gps)
		gtk.main()
		
	def expose_event(self, widget, event):
		x , y, width, height = event.area
		widget.window.draw_drawable(widget.get_style().fg_gc[gtk.STATE_NORMAL],
			pixmap, x, y, x, y, width, height)
			
		return False

	def configure_event(self, widget, event):
		global pixmap
		global xgc
		global last_display_data
		x, y, width, height = widget.get_allocation()
		pixmap = gtk.gdk.Pixmap(widget.window, width, height)
		pixmap.draw_rectangle(widget.get_style().bg_gc[gtk.STATE_NORMAL],
			True, 0, 0, width, height)
		xgc = widget.window.new_gc()
		xgc.line_width = 3
		self.drawing_area_configured = True
		last_display_data = None
		
	def draw_arrow(self):
		if (not self.drawing_area_configured):
			return False
			
		global arrow_transformed
		global last_display_data
		global last_arrow_bounds
		
		disabled = not self.has_fix
		widget = drawing_area
		x, y, width, height = widget.get_allocation()
		
		if disabled:		
			xgc.set_rgb_fg_color(gtk.gdk.color_parse("red"))
			pixmap.draw_line(xgc, 0, 0, width, height)
			pixmap.draw_line(xgc, 0, height, width, 0)
			widget.window.draw_drawable(widget.get_style().fg_gc[gtk.STATE_NORMAL],
			pixmap, 0, 0, 0, 0, width, height)
		
			last_display_data = None
			return False
			
		display_bearing = self.gps_position.bearing_to(self.target_position) - self.gps_bearing
		display_distance = self.target_distance
		
		if (display_distance < 50):
			color = "red"
		elif (display_distance < 150):
			color = "orange"
		else:
			color = "green"
		
		display_data = (display_bearing, color)
		if display_data == last_display_data:
			return False
		
		if arrow_transformed != None and last_display_data != None and last_arrow_bounds != None:
			minx, miny, maxx, maxy = last_arrow_bounds
		else:
			minx = 0
			miny = 0
			maxx = width
			maxy = height
		
		pixmap.draw_rectangle( widget.get_style().bg_gc[gtk.STATE_NORMAL],
			True, minx, miny, maxx, maxy)
		arrow_transformed = self.get_arrow_transformed(width, height, display_bearing)	
		
		minx = min(b[0] for b in arrow_transformed)-10
		miny = min(b[1] for b in arrow_transformed)-10
		maxx = max(b[0] for b in arrow_transformed)+10
		maxy = max(b[1] for b in arrow_transformed)+10
		last_arrow_bounds = [minx,  miny, maxx, maxy]
			
		xgc.set_rgb_fg_color(gtk.gdk.color_parse(color))
		pixmap.draw_polygon(xgc, True, arrow_transformed)
		xgc.set_rgb_fg_color(gtk.gdk.color_parse("black"))
		pixmap.draw_polygon(xgc, False, arrow_transformed)	
		
		widget.window.draw_drawable(widget.get_style().fg_gc[gtk.STATE_NORMAL],
			pixmap, 0, 0, 0, 0, width, height)
		
		last_display_data = display_data
		return False

	def get_arrow_transformed(self, width, height, angle):
		arrow = [(0, -1.66), (1, +1.33), (0,0.33), (-1, 1.33)]
		multiply = height / (2.0*1.66)
		offset_x = width / 2 
		offset_y = height / 2 
		s = math.sin(math.radians(angle))
		c = math.cos(math.radians(angle))
		at = []
		for (x, y) in arrow:
			at.append((int(x * multiply * c + offset_x - y * multiply * s),
				int(y * multiply * c + offset_y + x * multiply * s)))
		return at
		
	def read_config(self):
		config = ConfigParser.ConfigParser()
		config.read(os.path.expanduser('~/.simplecaching.conf'))
		if not config.has_section("saved"): #or not config.has_option("saved","last_target_lat") or not has_option("saved","last_target_lon"):
			target_lat = 49.23456
			target_lon = 6.23456
		else:
			target_lat = config.get("saved","last_target_lat",0)
			target_lon = config.get("saved", "last_target_lon",0)

		self.target_position = Coordinate(float(target_lat), float(target_lon))
		if not config.has_section("stored targets"):
			return
			
		i = 0
		self.stored_targets = []
		while (config.has_option("stored targets", "stored-%d-lat" % i) and 
			config.has_option("stored targets", "stored-%d-lon" % i) and
			config.has_option("stored targets", "stored-%d-name" % i)):
			stored_lat = config.get("stored targets", "stored-%d-lat" % i, 0)
			stored_lon = config.get("stored targets", "stored-%d-lon" % i, 0)
			stored_name = config.get("stored targets", "stored-%d-name" % i, 0)
			self.stored_targets.append(Coordinate(float(stored_lat), float(stored_lon), stored_name))
			i = i + 1
		
	def write_config(self):
		config = ConfigParser.ConfigParser()
		config.add_section("saved")
		config.set("saved", "last_target_lat", "%8.5f" % self.target_position.lat)
		config.set("saved", "last_target_lon", "%9.5f" % self.target_position.lon)
		
		config.add_section("stored targets")
		i = 0
		for pos in self.stored_targets:
			config.set("stored targets", "stored-%d-lat" % i, "%8.5f" % pos.lat)
			config.set("stored targets", "stored-%d-lon" % i, "%8.5f" % pos.lon)
			config.set("stored targets", "stored-%d-name" % i, "%s" % pos.name)
			i = i + 1
		config.write(open(os.path.expanduser('~/.simplecaching.conf'),'w'))

	def show_coordinate_input(self, start):
		name = start.name
		udr = Updown_Rows(self.format, start)
		dialog = gtk.Dialog("Change Target", None, gtk.DIALOG_MODAL, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
		
		frame = gtk.Frame("Latitude")
		frame.add(udr.table_lat)
		dialog.vbox.pack_start(frame)
		
		frame = gtk.Frame("Longitude")
		frame.add(udr.table_lon)
		dialog.vbox.pack_start(frame)
		
		dialog.show_all()
		dialog.run()
		dialog.destroy()
		c = udr.get_value()
		c.name = name
		return c
		
	def input_target(self, target):
		self.target_position = self.show_coordinate_input(self.target_position)
		self.update_target_display();
		self.write_config()				

	def switch_display(self, target):
		if self.format == self.FORMAT_D:
			self.format = self.FORMAT_DM
		elif self.format == self.FORMAT_DM:
			self.format = self.FORMAT_D

		self.update_display()
		self.update_target_display()

	def read_gps(self):
		gps_data = self.gps_thread.get_data()
		if (gps_data['position'] != None):
			self.gps_position = gps_data['position']
			self.gps_bearing = gps_data['bearing']
			self.gps_altitude = gps_data['altitude']
			self.gps_speed = gps_data['speed']
			self.gps_sats = gps_data['sats']
			self.gps_sats_known = gps_data['sats_known']
			self.on_good_fix()
		else:
			self.gps_sats = gps_data['sats']
			self.gps_sats_known = gps_data['sats_known']
			self.on_no_fix()
		return True
		
	def on_good_fix(self):
		self.target_distance = self.gps_position.distance_to(self.target_position)
		self.update_display()
		self.has_fix  = True
		self.draw_arrow()
		self.update_progressbar()
		
	def on_no_fix(self):
		labelBearing.set_text("No Fix")
		labelLatLon.set_text(self.gps_thread.status)
		self.has_fix = False
		self.draw_arrow()
		self.update_progressbar()
		
	def update_display(self):
		labelBearing.set_text("%d°" % self.gps_bearing)
			
		if self.target_distance >= 1000:
			labelDist.set_text("%3dkm" % round(self.target_distance / 1000))
		elif display_dist >= 100:
			labelDist.set_text("%3dm" % round(self.target_distance))
		else:
			labelDist.set_text("%2.1fm" % round(self.target_distance,1))

		labelAltitude.set_text("%3dm" % self.gps_altitude)
		labelLatLon.set_text("Current: %s / %s" % (self.gps_position.get_lat(self.format), self.gps_position.get_lon(self.format)))

	def update_progressbar(self):
		progressbar.set_fraction(float(self.gps_sats)/12.0)
		progressbar.set_text("Satellites: %d/%d" % (self.gps_sats, self.gps_sats_known))
		
	def update_target_display(self):
		labelTargetLatLon.set_text("Target: %s / %s" % (self.target_position.get_lat(self.format), self.target_position.get_lon(self.format)))
		
	
	def destroy(self, target):
		gtk.main_quit()



class Gps_reader():
	def __init__(self, gui):
		self.gui = gui
		self.status = "connecting..."
		self.connect()
		
	
	def connect(self):
		try:
			global gpsd_connection
			gpsd_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			gpsd_connection.connect(("127.0.0.1", 2947))
			self.status = "connected"
		except:
			self.status = "Could not connect to GPSD on Localhost, Port 2947"
			print "Could not connect"
		
	def get_data(self):
		try:
			gpsd_connection.send("%s\r\n" % 'o')
			data = gpsd_connection.recv(512)
			gpsd_connection.send("%s\r\n" % 'y')
			quality_data = gpsd_connection.recv(512)
			
			# 1: Parse Quality Data
			
			# example output:
			# GPSD,Y=- 1243847265.000 10:32 3 105 0 0:2 36 303 20 0:16 9 65 26 
			#  1:13 87 259 35 1:4 60 251 30 1:23 54 60 37 1:25 51 149 24 0:8 2 
			#  188 0 0:7 33 168 24 1:20 26 110 28 1:
			
			if quality_data == "GPSD,Y=?":
				sats = 0
				sats_known = 0
			else:
				sats = 0
				groups = quality_data.split(':')
				sats_known = int(groups[0].split(' ')[2])
				for i in range(1, sats_known):
					if groups[i].split(' ')[4] == "1":
						sats = sats + 1
							
			if data.strip() == "GPSD,O=?":
				self.status = "No GPS signal"
				return {
					'position': None,
					'altitude': None,
					'bearing': None,
					'speed': None,
					'sats': sats,
					'sats_known': sats_known
				}
				
			# 2: Get current position, altitude, bearing and speed
			
			# example output:
			# GPSD,O=- 1243530779.000 ? 49.736876 6.686998 271.49 1.20 1.61 49.8566 0.050 -0.175 ? ? ? 3
			# or
			# GPSD,O=?
			try:
				[tag, timestamp, time_error, lat, lon, alt, err_hor, err_vert, track, speed, delta_alt, err_track, err_speed, err_delta_alt, mode] = data.split(' ')
			except:
				print "GPSD Output: \n%s\n  -- cannot be parsed." % data
				self.status = "Could not read GPSD output."
				
			return {
				'position': Coordinate(float(lat), float(lon)),
				'altitude': float(alt),
				'bearing': float(track),
				'speed': float(speed),
				'sats': int(sats),
				'sats_known': sats_known
			}
		except:
			#print "Fehler beim Auslesen der Daten."
			return {
				'position': None,
				'altitude': None,
				'bearing': None,
				'speed': None,
				'sats': 0,
				'sats_known': 0
			}

		
	

if __name__ == "__main__":
	gtk.gdk.threads_init()
	gui = Gui()

