if __name__ == '__main__':
    import ModuleUpdate
    ModuleUpdate.update()

    import Utils
    Utils.init_logging("CotNDClient", exception_logger="Client")

    from worlds.cotnd.Client import launch
    launch()
