import tkinter as tk
from tkinter import ttk
from PIL import ImageTk, Image, ImageOps, ImageDraw, UnidentifiedImageError
from tkinter import filedialog as fd
from tkinter import messagebox
from pandas import read_csv, errors
import serial
import serial.tools.list_ports
from serial.serialutil import SerialException

# import sys
# class MockSerial():

#     ''' Mock serial class for testing the GUI without an Arduino '''

#     def __init__(self):
#         self.colcount = 0

#     ''' Write data to stdout instead of to the serial port'''
#     def write_data(self, data):
#         sys.stdout.write(str(data))
#         self.colcount += 1
#         if self.colcount > 78:
#             sys.stdout.write('\n')
#             self.colcount = 0
#         sys.stdout.flush()
#         if(len(data) > 1):
#             print('\n')
#             self.print_list_as_matrix([int(item) for item in data], 8, 8)

#     ''' Print given list as a num_col by num_row matrix '''
#     def print_list_as_matrix(self, lst, num_col, num_row):
#         for row in range(num_row):
#             for col in range(num_col):
#                 print(lst[row*num_col + col], end='\t')
#             print('\n')


class ArduinoPort():

    ''' Serial port for communicating with the Arduino '''

    def __init__(self):
        port = self.get_arduino_port()
        self.serial_writer = serial.Serial(port, 115200)

    ''' Get port name for the connected Arduino with the lowest COM port ID '''
    def get_arduino_port(self):
        arduino_ports = [
            p.device
            for p in serial.tools.list_ports.comports()
            if p.vid in [0x2341, 0x2A03, 0x1B4F, 0x239A, 0x1A86]  # vendor IDs
        ]
        if not arduino_ports:       # No Arduinos found
            return None
        if len(arduino_ports) > 1:
            message = "More than one Arduino is currently connected.\n"
            message += "Selecting Arduino with the lowest COM port ID..."
            messagebox.showwarning("Multiple Arduinos Detected", message)
        return arduino_ports[0]

    ''' Send data to the connected Arduino over the serial COM port '''
    def write_data(self, data):
        if not data:
            message = "Error loading pixel_vals data.\n"
            message += "Try reloading a file or restarting the application."
            messagebox.showerror("No Serial Data Found", message)
            return
        try:
            self.serial_writer.write('<data>'.encode())
            self.serial_writer.write(data)
            self.serial_writer.write('</data>'.encode())
        except SerialException:
            message = "The Arduino was disconnected or has changed COM ports.\n"
            message += "Try resending the data, using a different USB port,"
            message += " or restarting the application."
            messagebox.showerror("Arduino Connection Error", message)
            self.serial_writer.close()
            self.serial_writer = serial.Serial(self.get_arduino_port(), 115200)


class Application(ttk.Frame):

    ''' The main GUI frame '''

    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        # get the arduino port number
        self.arduino = ArduinoPort() # MockSerial()
        # create an array of pixel values
        self.pixel_vals = []
        # create any widgets to display in the frame
        self.create_widgets()
        # display self on the parent window
        self.grid()

    def create_widgets(self):
        ## IMAGES
        # display input image
        self.lif_input = LabeledImageFrame(self, "Input Image")
        self.lif_input.grid(row=0, column=0, padx=10, pady=10)
        # display grayscale version of input image
        self.lif_grayscale = LabeledImageFrame(self, "Grayscale Image")
        self.lif_grayscale.grid(row=0, column=1, padx=10, pady=10)
        # display pixelized version of grayscale image
        self.lif_pixelize = LabeledImageFrame(self, "Pixelized Image")
        self.lif_pixelize.grid(row=0, column=2, padx=10, pady=10)        
        # display pattern preview with labeled pixel brightness values
        self.lif_pattern = LabeledImageFrame(self, "Pattern Preview")
        self.lif_pattern.grid(row=1, column=0, padx=10, pady=10,
            columnspan=2, rowspan=5)
        # initial image on application load
        init_img = Image.open("Resource/Images/init_img.png")
        init_img = init_img.resize((130, 130), Image.ANTIALIAS)
        self.set_input_image(init_img)

        ## BUTTONS
        # import image
        btn_import_img = ttk.Button(self, width=12, text="Import Image",
            command=self.import_image)
        btn_import_img.grid(row=1, column=2, sticky="S", pady=0)
        # import .csv
        btn_import_csv = ttk.Button(self, width=12, text="Import .CSV",
            command=self.import_csv)
        btn_import_csv.grid(row=2, column=2, sticky="S", pady=0)
        # reset (turn off all LEDs)
        btn_reset = ttk.Button(self, width=12, text="Reset",
            command=self.reset_leds)
        btn_reset.grid(row=3, column=2, sticky="S", pady=0)
        # serial write data
        btn_serial_write = ttk.Button(self, width=12, text="Send Data",
            command=self.serial_write_data)
        btn_serial_write.grid(row=4, column=2, sticky="S", pady=0)

    ''' Write pixel values to the Arduino serial port '''
    def serial_write_data(self):
        serial_data = bytearray(self.pixel_vals)
        self.arduino.write_data(serial_data)

    ''' Updates all images and pixel data after importing a new input image '''
    def set_input_image(self, image):
        # input image
        img = ImageTk.PhotoImage(image)
        self.lif_input.set_image(img)
        # grayscale image
        gray_img = ImageOps.grayscale(image)
        img = ImageTk.PhotoImage(gray_img)
        self.lif_grayscale.set_image(img)
        # pixelized image
        pattern_img = gray_img.resize((8, 8))
        pixelize_img = pattern_img.resize(gray_img.size, Image.NEAREST)
        img = ImageTk.PhotoImage(pixelize_img)
        self.lif_pixelize.set_image(img)
        # pattern preview
        self.pixel_vals = list(pattern_img.getdata())
        preview_img = self.draw_pattern_preview(pattern_img)
        img = ImageTk.PhotoImage(preview_img)
        self.lif_pattern.set_image(img)

    ''' Load an image file into the GUI for processing '''
    def import_image(self):
        filename = fd.askopenfilename(title="Open Image", 
            filetypes= (("All Image Files", ".png .jpeg .gif .jfif .bmp .dds" + 
            " .dib .eps .icns .ico .im .j2k .j2p .jpx .msp .pcx .apng .ppm" +
            " .sgi .spider .tga .tiff .webp .xbm"), ("All Files", "*")))
        if filename:
            try:
                img = Image.open(filename)
            except UnidentifiedImageError:
                message = "An unsupported image file type was selected.\n"
                message += "Suggested file types are .PNG and .JPEG."
                messagebox.showerror("Unidentified Image Error", message)
                return
            img = img.resize((130, 130), Image.ANTIALIAS)
            self.set_input_image(img)

    ''' Load a pre-processed .csv file '''
    def import_csv(self):
        filename = fd.askopenfilename(title="Open .CSV",
            filetypes=((".CSV Files", "*.csv"), ("All Files", "*")))
        if filename:
            try:
                df = read_csv(filename, header=None, prefix='Column ')
            except (errors.ParserError, UnicodeDecodeError):
                message = "An unsupported file type was selected.\n"
                message += "Only .CSV files may be read in this method."
                messagebox.showerror("Unrecognized File Format", message)
                return
            self.pixel_vals = []
            for row in df.values:
                self.pixel_vals += list(row)
            self.generate_images_from_pixel_vals()

    ''' Reset all LEDs to off state '''
    def reset_leds(self):
        serial_data = bytearray([0] * 64)
        self.arduino.write_data(serial_data)

    ''' Update the images to reflect the state of pixel_vals after .csv load '''
    def generate_images_from_pixel_vals(self):
        pattern_img = Image.new('L', (8,8))
        pattern_img.putdata(self.pixel_vals)
        img = pattern_img.resize((130,130), Image.NEAREST)
        img = ImageTk.PhotoImage(img)
        self.lif_input.set_image(img)
        self.lif_grayscale.set_image(img)
        self.lif_pixelize.set_image(img)
        img = self.draw_pattern_preview(pattern_img)
        img = ImageTk.PhotoImage(img)
        self.lif_pattern.set_image(img)

    ''' Generate the pattern preview '''
    def draw_pattern_preview(self, pattern_img):
        scaling_factor = 37
        width, height = pattern_img.size
        preview_img = pattern_img.resize((width*scaling_factor, 
            height*scaling_factor), Image.NEAREST)
        draw = ImageDraw.Draw(preview_img)
        for row in range(height):
            for col in range(width):
                val = pattern_img.getpixel((col, row))
                if val > 127:
                    draw.text((col*scaling_factor, row*scaling_factor), 
                        str(val), fill=0)
                else:
                    draw.text((col*scaling_factor, row*scaling_factor), 
                        str(val), fill=255)
        return preview_img


class LabeledImageFrame(ttk.LabelFrame):

    ''' A labeled frame containing an image '''
    
    def __init__(self, parent, text, photo_image=None):
        ttk.LabelFrame.__init__(self, parent, text=text)
        self["labelanchor"] = tk.N
        self.img = photo_image
        self.create_widgets()
    
    ''' Display the image in a label '''
    def create_widgets(self):
        self.lbl_img = ttk.Label(self, image=self.img)
        self.lbl_img.grid(padx=5, pady=5)

    ''' Set the image to display '''
    def set_image(self, photo_image):
        self.img = photo_image
        self.lbl_img["image"] = self.img


def main():
    root = tk.Tk()
    root.title("LED Matrix Configurator")
    root.iconphoto(False, tk.PhotoImage(file='Resource/Images/icon.png'))

    root.tk.call("source", "Resource/Theme/forest-dark.tcl")
    ttk.Style().theme_use("forest-dark")

    app = Application(root)
    root.mainloop()


if __name__ == '__main__': main()