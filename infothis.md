Use 'Show-Help' to display help
~\Projects\MAMcrawler  006-whispered-plusplus  ?325 ~1  1  cd C:\Users\dogma\Projects\MAMcrawler
~\Projects\MAMcrawler  006-whispered-plusplus  ?325 ~1  1    python RUN_THIS.py
2025-11-17 07:50:51,204 | 
2025-11-17 07:50:51,204 | ================================================================================
2025-11-17 07:50:51,204 | AUDIOBOOKSHELF SERIES POPULATOR - AUTOMATIC
2025-11-17 07:50:51,204 | ================================================================================
2025-11-17 07:50:51,205 | 
2025-11-17 07:50:51,205 | [STEP 1/5] Checking current status...
2025-11-17 07:50:52,007 |   Audiobookshelf is currently running
2025-11-17 07:50:52,007 | Stopping Audiobookshelf...
SUCCESS: The process "node.exe" with PID 20356 has been terminated.
--- Logging error ---
Traceback (most recent call last):
  File "C:\Program Files\Python311\Lib\logging\__init__.py", line 1113, in emit
    stream.write(msg + self.terminator)
  File "C:\Program Files\Python311\Lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 26: character maps to <undefined>
Call stack:
  File "C:\Users\dogma\Projects\MAMcrawler\RUN_THIS.py", line 196, in <module>
    sys.exit(main())
  File "C:\Users\dogma\Projects\MAMcrawler\RUN_THIS.py", line 129, in main
    stop_abs()
  File "C:\Users\dogma\Projects\MAMcrawler\RUN_THIS.py", line 93, in stop_abs
    logger.info("✓ Audiobookshelf is now stopped")
Message: '✓ Audiobookshelf is now stopped'
Arguments: ()
2025-11-17 07:50:55,544 | ✓ Audiobookshelf is now stopped
2025-11-17 07:50:55,548 |
2025-11-17 07:50:55,548 | [STEP 2/5] Starting Audiobookshelf (schema repair)...
2025-11-17 07:50:55,549 | Attempting to start Audiobookshelf...
2025-11-17 07:50:59,061 | ! Could not start Audiobookshelf automatically
2025-11-17 07:50:59,061 |   Please start Audiobookshelf manually and press Enter
  Press Enter when Audiobookshelf is running...
--- Logging error ---
Traceback (most recent call last):
  File "C:\Program Files\Python311\Lib\logging\__init__.py", line 1113, in emit
    stream.write(msg + self.terminator)
  File "C:\Program Files\Python311\Lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'charmap' codec can't encode character '\u2717' in position 26: character maps to <undefined>
Call stack:
  File "C:\Users\dogma\Projects\MAMcrawler\RUN_THIS.py", line 196, in <module>
    sys.exit(main())
  File "C:\Users\dogma\Projects\MAMcrawler\RUN_THIS.py", line 136, in main
    if not start_abs():
  File "C:\Users\dogma\Projects\MAMcrawler\RUN_THIS.py", line 76, in start_abs
    logger.error("✗ Audiobookshelf is still not running")
Message: '✗ Audiobookshelf is still not running'
Arguments: ()
2025-11-17 07:51:26,530 | ✗ Audiobookshelf is still not running
2025-11-17 07:51:26,533 | Could not start Audiobookshelf