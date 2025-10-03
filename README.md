MalieUnRepaker_Camellia-ver.
======
A dedicated unpack/repack tool for the Malie engine, written in Python, along with its source code.

The Malie engine unpacking code used in this tool was forked from [GARbro](https://github.com/morkt/GARbro)  [v1.1.6](https://github.com/morkt/GARbro/releases/tag/v1.1.6) (by  by  [morkt](https://github.com/morkt/GARbro)) and ported to the Python programming language.

The Camellia decryption key table list is derived from code written by morkt and [asmodean](http://asmodean.reverse.net)
, the author of [exdieslib](https://github.com/regomne/chinesize/blob/master/Malie/exdieslib/exdieslib.cpp)
.
Many thanks to them for their work.


Supported games
======
※ All Malie engine archives that use the 「Camellia encryption algorithm」 can be fully unpacked and repacked.

Caution
======
1. The current repack code with encryption is not recognized by the game due to unresolved issues. Only plaintext (unencrypted) repacking is supported at this time.
2. Due to a limitation of the engine, filenames longer than 20 bytes will be truncated and not recognized in-game. You must manually shorten them using a hex editor.

Credits
======
## Original author
- **morkt**  — Original author of [GARbro](https://github.com/morkt/GARbro), from which the unpacking logic was ported.
- **asmodean**  — Created the original Camellia key table used for Malie engine decryption.
## Special Thanks
- **Neidhardt** — Deepest thanks for your technical support and kind assistance.

