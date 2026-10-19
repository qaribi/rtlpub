# Changelog

## Unreleased

- Check structural BCP 47 tags in EPUB metadata and all XHTML language
  declarations, including complex, private-use and grandfathered forms.
- Add language-tag errors without changing JSON schema 1.0 or advisory
  language-conflict behavior. Registry validation remains outside scope.

## 0.1.0

Initial implementation of offline Persian/RTL text, XHTML and EPUB 3 preflight.
Stable JSON schema 1.0, configurable severity thresholds and controlled errors.
Bounded ZIP/XML parsing, synthetic fixtures and input safety regression tests.
No auto-fix, runtime third-party dependencies, DRM handling or network fetching.
