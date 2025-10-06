MalieUnRepaker_Camellia-ver.
======
A dedicated unpack/repack tool for the Malie engine, written in Python, along with its source code.

The Malie engine unpacking code used in this tool was forked from [GARbro](https://github.com/morkt/GARbro)  [v1.1.6](https://github.com/morkt/GARbro/releases/tag/v1.1.6) (by  by  [morkt](https://github.com/morkt/GARbro)) and ported to the Python programming language.

The Camellia decryption key table list is derived from code written by morkt and [asmodean](http://asmodean.reverse.net)
, the author of [exdieslib](https://github.com/regomne/chinesize/blob/master/Malie/exdieslib/exdieslib.cpp)
.
Many thanks to them for their work.

Caution
======
1. The current repack code with encryption is not recognized by the game due to unresolved issues. Only plaintext (unencrypted) repacking is supported at this time.
2. Due to a limitation of the engine, filenames longer than 20 bytes will be truncated and not recognized in-game. You must manually shorten them using a hex editor.
3. This tool is intended for use only with Malie engine archives that utilize the Camellia encryption algorithm. It does not work with newer versions of the Malie engine.
4. The Malie engine does not maintain a consistent file region order, and its file index table is further complicated by hierarchical directories. Therefore, during unpacking this tool generates a metadata.json file containing all directory and file information. When repacking, this JSON file is required, as it preserves and reproduces both the file order and entry index sequence.

Supported games
======
※ All Malie engine archives that use the 「Camellia encryption algorithm」 can be fully unpacked and repacked.
- Omerta -Chinmoku no Okite- (オメルタ -沈黙の掟-) ※BL
- Omerta CODE:TYCOON (オメルタ CODE:TYCOON) ※BL
- Omega Vampire (オメガヴァンパイア) ※BL
- Danzai no Maria -The Exorcism of Maria- (断罪のマリア　THE EXORCISM OF MARIA)
- Zettai Meikyuu Grimm -Nanatsu no Kagi to Rakuen no Otome- (絶対迷宮グリム -七つの鍵と楽園の乙女-)
- Paradise Lost
- Dies irae
- Kajiri Kamui Kagura Premier Trial (神咒神威神楽 体験版)
- Kajiri Kamui Kagura (神咒神威神楽)
- Kajiri Kamui Kagura Akebono no Hikari (神咒神威神楽 曙之光)
- Zero Infinity -Devil of Maxwell-
- Electro Arms -Realize Digital Dimension-
- Soushuu Senshinkan Gakuen: Hachimyoujin (相州戦神館學園 八命陣)

User manual
======
- [Korean ver.](https://note.com/sechskatze_note/n/n71fb8b96e78f)

Credits
======
## Original author
- **morkt**  — Original author of [GARbro](https://github.com/morkt/GARbro), from which the unpacking logic was ported.
- **asmodean**  — Created the original Camellia key table used for Malie engine decryption.
## Special Thanks
- **Neidhardt** — Deepest thanks for your technical support and kind assistance.
- **[DanOl98](https://github.com/DanOl98)** — The layout design of the Malie UnRepacker GUI version is based on [MagesPack](https://github.com/DanOl98/MagesPack).
