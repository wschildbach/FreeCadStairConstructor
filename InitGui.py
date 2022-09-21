class Stairs2Workbench (Workbench):

    MenuText = "Stairs2"

    def Initialize(self):
        import makeStairs
        import makeStairPath
        commandslist = ["makeStairPath","makeStairs"]
        self.appendToolbar("Stairs", commandslist)

Gui.addWorkbench(Stairs2Workbench())
