class Styles:

    defaultStyle = "QPushButton { font-size: 8px }"
    darkStyle = ""

    def __init__(self):

        with open("vi/ui/res/styles/dark.css") as dark:
            self.darkStyle = dark.read()

    def getStyles(self):
        return ["default", "darkstyle"]

    def getStyle(self, style):
        if (style == "default"):
            return self.defaultStyle
        elif style == "darkstyle":
            return self.darkStyle
        else:
            return ""