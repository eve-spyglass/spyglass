import logging
import yaml

class Styles:

    defaultStyle = ""
    defaultCommons = ""

    darkStyle = ""
    darkCommons = ""

    styleList = ["default", "darkstyle"]

    currentStyle = "default"

    def __init__(self):

        #default theme
        with open("vi/ui/res/styles/default.css") as default:
            Styles.defaultStyle = default.read()
        with open("vi/ui/res/styles/default.yaml") as default:
            Styles.defaultCommons = yaml.load(default)
        default = None

        #dark theme
        with open("vi/ui/res/styles/dark.css") as dark:
            Styles.darkStyle = dark.read()
        with open("vi/ui/res/styles/dark.yaml") as dark:
            Styles.darkCommons = yaml.load(dark)
        dark = None


    def getStyles(self):
        return self.styleList

    def getStyle(self):
        if (Styles.currentStyle == "default"):
            return self.defaultStyle
        elif Styles.currentStyle == "darkstyle":
            return self.darkStyle
        else:
            return ""

    def getCommons(self):
        if (Styles.currentStyle == "default"):
            return Styles.defaultCommons
        elif Styles.currentStyle == "darkstyle":
            return Styles.darkCommons
        else:
            return ""

    def setStyle(self, style):
        if style in Styles.styleList:
            Styles.currentStyle = style
        else:
            logging.critical("Attempted to switch to unknown style: {}".format(style))

class TextInverter():

    def getTextColourFromBackground(self, colour):
        if colour[0] is '#':
            colour = colour[1:]
        red = int(colour[0:2], 16)
        green = int(colour[2:4], 16)
        blue = int(colour[4:6], 16)

        #perceptive Luminance formula
        perc = 1 - (((0.299 * red) + (0.587 * green) + (0.114 * blue)) / 255)
        if perc < 0.5:
            return "#000000"
        else:
            return "#FFFFFF"

if __name__ == "__main__":
    inv = TextInverter()
    print "50E661"
    print (inv.getTextColourFromBackground("50E661"))