# audiobookshelf

**Source:** https://www.audiobookshelf.org/guides/book-scanner

**Crawled:** 2025-11-27 21:19:31

---

# Book Scanner

This guide describes how the book scanner works as of serverv2.5.0.

`v2.5.0`Book grouping is different from metadata parsing, with books being defined by directory due to how the data is stored in the database. The metadata parsing is how metadata is applied to the book, and does not take priority over the book grouping. This scanning occurs locally with no automatic lookups with online metadata providers. To get metadata from an online provider, you will need to perform a Match operation on the media or library.

## tagBook library scanner steps



- Library is scanned and files are grouped into books.Each audio and ebook files in the root of a library folder are considered an individual booksOtherwise, every folder with a supported media file is considered to be a book (including subfolders of the top folder)Ebook files are ignored if scanning an "Audiobooks only" library
- Each audio and ebook files in the root of a library folder are considered an individual books
- Otherwise, every folder with a supported media file is considered to be a book (including subfolders of the top folder)
- Ebook files are ignored if scanning an "Audiobooks only" library
- Check for missing books (priority given to filepath, falls back toinode valueto handle renames)All books in the library are checked to see if any are missingBooks can also be set as missing if all audio and ebook files are removed
- All books in the library are checked to see if any are missing
- Books can also be set as missing if all audio and ebook files are removed
- Each book found by the scanner is checked to see if it already exists in the library. If a book already exists, it is checked for updates. If this is a new book, the same steps are made.Newly added or modified audio files are probed (usingffprobe)Audio tracks are orderedEbook files are checkedIf not "Audiobook only" library, primary ebook is set with priority given toepubformat.All other supported ebook formats are added as supplementaryCover image is cleared if missing. If no cover is set, an attempt is made to set the cover.Cover image is set using an image file in the folder, priority given to files named "cover"Otherwise, check for image embedded in audio fileOtherwise, check for image in an epub or comic book fileOtherwise, if "Find covers" server setting is enabled search online for a cover (Note: This setting is planned to be replaced by a more comprehensize lookup)Book metadata is parsed according to configured priority, shown further down this pageThemetadata.jsonis created or updated accordingly.
- Newly added or modified audio files are probed (usingffprobe)
- Audio tracks are ordered
- Ebook files are checkedIf not "Audiobook only" library, primary ebook is set with priority given toepubformat.All other supported ebook formats are added as supplementary
- If not "Audiobook only" library, primary ebook is set with priority given toepubformat.
- All other supported ebook formats are added as supplementary
- Cover image is cleared if missing. If no cover is set, an attempt is made to set the cover.Cover image is set using an image file in the folder, priority given to files named "cover"Otherwise, check for image embedded in audio fileOtherwise, check for image in an epub or comic book fileOtherwise, if "Find covers" server setting is enabled search online for a cover (Note: This setting is planned to be replaced by a more comprehensize lookup)
- Cover image is set using an image file in the folder, priority given to files named "cover"
- Otherwise, check for image embedded in audio file
- Otherwise, check for image in an epub or comic book file
- Otherwise, if "Find covers" server setting is enabled search online for a cover (Note: This setting is planned to be replaced by a more comprehensize lookup)
- Book metadata is parsed according to configured priority, shown further down this page
- Themetadata.jsonis created or updated accordingly.
- Authors and series are checked for removalAuthors are removed if they have no books and have no additional metadata set (image, description or asin)Series are removed if they have no books
- Authors are removed if they have no books and have no additional metadata set (image, description or asin)
- Series are removed if they have no books

- Each audio and ebook files in the root of a library folder are considered an individual books
- Otherwise, every folder with a supported media file is considered to be a book (including subfolders of the top folder)
- Ebook files are ignored if scanning an "Audiobooks only" library

- All books in the library are checked to see if any are missing
- Books can also be set as missing if all audio and ebook files are removed

- Newly added or modified audio files are probed (usingffprobe)
- Audio tracks are ordered
- Ebook files are checkedIf not "Audiobook only" library, primary ebook is set with priority given toepubformat.All other supported ebook formats are added as supplementary
- If not "Audiobook only" library, primary ebook is set with priority given toepubformat.
- All other supported ebook formats are added as supplementary
- Cover image is cleared if missing. If no cover is set, an attempt is made to set the cover.Cover image is set using an image file in the folder, priority given to files named "cover"Otherwise, check for image embedded in audio fileOtherwise, check for image in an epub or comic book fileOtherwise, if "Find covers" server setting is enabled search online for a cover (Note: This setting is planned to be replaced by a more comprehensize lookup)
- Cover image is set using an image file in the folder, priority given to files named "cover"
- Otherwise, check for image embedded in audio file
- Otherwise, check for image in an epub or comic book file
- Otherwise, if "Find covers" server setting is enabled search online for a cover (Note: This setting is planned to be replaced by a more comprehensize lookup)
- Book metadata is parsed according to configured priority, shown further down this page
- Themetadata.jsonis created or updated accordingly.

- If not "Audiobook only" library, primary ebook is set with priority given toepubformat.
- All other supported ebook formats are added as supplementary

`epub`- Cover image is set using an image file in the folder, priority given to files named "cover"
- Otherwise, check for image embedded in audio file
- Otherwise, check for image in an epub or comic book file
- Otherwise, if "Find covers" server setting is enabled search online for a cover (Note: This setting is planned to be replaced by a more comprehensize lookup)

`metadata.json`- Authors are removed if they have no books and have no additional metadata set (image, description or asin)
- Series are removed if they have no books

## tagBook metadata parsing



Metadata priority is set in the "Scanner" tab of the library settings. Lower priority sources can fill empty fields if a higher priority metadata source does not include that information.

NOTE: This is unintuitive in2.5.0since the highest priority is visibly lower due a "fill order" being displayed. This is changed in2.6.0to better reflect a priority order. In2.5.0the item with the lowest priority (1) fills the data it has if enabled. The second lowest priority (2) then fills its data, overwriting any duplicate fields from the previous step.

`2.5.0``2.6.0``2.5.0`### tagFolder structure

Book metadata is pulled from folder names according to thedirectory structure,author folder namingandtitle folder namingdocs.
The following metadata can be pulled from here: title, subtitle, asin, authors, narrators, series, series sequence, and published year.

### tagAudio file meta tags OR ebook metadata

Audio file meta tags are found fromffprobe. After the audio files are sorted into track order (only) the first audio file will be checked for meta tags following theaudio metadatadocs.

As ofv2.7.2epub and comic book metadata will pulled if the book has no audio files.

`v2.7.2`### tagdesc.txt & reader.txt files

If a file nameddesc.txtis found in the books folder it will be used as the description. If a file namedreader.txtis found in the books folder it will be used as the narrator.

`desc.txt``reader.txt`### tagOPF file

If a file with.opfextension is found in the books folder it will be parsed. (Example OPF file coming soon)

`.opf`### tagAudiobookshelf metadata file

Themetadata.jsonfile is automatically saved anytime book metadata is set. If the "Store metadata with item" server setting is enabled then the metadata file will be stored in the same folder as your book (only for books in subfolders). Otherwise, the metadata file is stored in/metadata/items/.

`metadata.json``/metadata/items/`Every book metadata field is stored in this file including chapters.

