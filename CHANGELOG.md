# Changelog

All notable changes to this project are documented in this file. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.0.2] - 2026-10-29

### Added

- Smart Picker entry "Meme (imgflip)": search imgflip's templates (the 100 most popular before the
  first search), edit the text boxes on the template, and insert the meme. Text boxes can be dragged,
  resized and rotated, and have their own font, alignment, colours and all caps.
- Rich preview of `https://i.imgflip.com/<slug>.<jpg|png>` and `https://imgflip.com/i/<slug>` links,
  at the width of the text column.
- Eight bundled fonts (Anton, Bebas Neue, Oswald, Bangers, Permanent Marker, Comic Neue, Roboto,
  Montserrat), each downloaded only when a box uses it. Anton stands in for Impact on devices without
  it.
- Upload cap of 10 MB, LRU caches of 100 templates and 100 images, and browser cache headers for
  templates, images and fonts.

### Changed

- The reference provider is unregistered when the app is disabled.

## [0.0.1]

- First version, from the Python ExApp skeleton.
