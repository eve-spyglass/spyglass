# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
    ffi=FixedFileInfo(
        # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
        # Set not needed items to zero 0.
        filevers=(2, 0, 1, 0),
        prodvers=(2, 0, 1, 0),
        # Contains a bitmask that specifies the valid bits 'flags'r
        mask=0x3F,
        # Contains a bitmask that specifies the Boolean attributes of the file.
        flags=0x0,
        # The operating system for which this file was designed.
        # 0x4 - NT and there is no need to change it.
        OS=0x4,
        # The general type of file.
        # 0x1 - the file is an application.
        fileType=0x1,
        # The function of the file.
        # 0x0 - the function is not defined for this fileType
        subtype=0x0,
        # Creation date and time stamp.
        date=(4, 22),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", "Crypta Tech"),
                        StringStruct("FileDescription", "spyglass"),
                        StringStruct("FileVersion", "2.0.1"),
                        StringStruct("InternalName", "Spyglass"),
                        StringStruct(
                            "LegalCopyright", "Copyright (c) Crypta Electrica"
                        ),
                        StringStruct("OriginalFilename", "spyglass.exe"),
                        StringStruct("ProductName", "Spyglass"),
                        StringStruct("ProductVersion", "2.0.1"),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)
