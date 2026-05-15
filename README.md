Overview:
Databender is my dissertation project for my informatics university. It's purpose is to create Glitch Art 
This dissertation addresses software development for data manipulation (databending) with the purpose of artistic corruption of digital Image files, as well as the education of the user. Additionally, the glitch production of different supported filetypes are analyzed.
The software allows byte level editing through two synchronized editors. A text editor with Latin-1 encoding is implemented for direct manipulation and understanding of the image structure. For precise modifications a Hex editor is developed, in which the user is able to edit the bytes of an image with hexadecimal representation.
The app supports eight file types (JPEG, PNG, BMP, GIF, TIFF, WEBP, PPM, TGA), specialized data manipulation tools (Randomize, Invert, Zero, Whitespace Inject, Repeat Chunks, Pattern Inject, Shuffle Blocks, Reverse Blocks, Hex Pattern Replace), clipboard management using the Pyperclip library, history management with undo, redo and reload, and custom selection range management. Moreover, a search function is implemented for the detection of offsets and hexadecimal values or patterns. The history and search functionalities feature a visual edit highlight system. 
The software is developed based on the Model View Controller design pattern coupled with an event bus using the Blinker library. The library Tkinter is used for the creation of the graphical interface, while the display, management and conversion of the file formats the library Pillow is used. Performance for large files up to 200MB is achieved with the implementation of a virtual scrolling system.
Evaluation of the application is performed through 122 unit tests for the backend components and manual tests, verified with corresponding figures. The resulting tool is complete, user‑friendly, and educational, emphasizing experimentation, suitable for both beginners and advanced glitch art practitioners.


Libraries needed:
- Pillow	≥ 9.0.0
- pyperclip	≥ 1.8.0
- blinker	≥ 1.6.0	
- tkinter

pip install pillow pyperclip blinker
