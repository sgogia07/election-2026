# ElectionCast Northern Virginia Newsroom upgrade

- Multi-source headline RSS aggregator (NPR, PBS, Virginia Mercury, WTOP, Google News fallback) preserving cached items during outages.
- Northern Virginia VA-07/08/10/11 and Virginia Senate candidate guides based on Virginia Department of Elections 2026 ballot lists.
- District result cards only show actual votes when district-specific figures are available from existing results adapter.
- Local/national headlines, publisher links, polling context and method caveats.
- Independent publisher YouTube player in browser only. FFmpeg uses ?broadcast=1 to hide it; external stream rebroadcast is not authorized.
- No invented polling numbers, winners or precinct breakdowns.
- STREAM_ENABLED remains false; enabling requires explicit authorization.
