//META: script=/resources/testdriver.js
//META: script=/resources/testdriver-vendor.js
//META: script=resources/test-expectations.js

'use strict';

font_access_test(async t => {
  const fonts = await navigator.fonts.query({persistentAccess: true});
  assert_true(Array.isArray(fonts), 'Result of query() should be an Array');
  assert_greater_than_equal(fonts.length, 1, 'Need a least one font');

  fonts.forEach(font => {
    assert_true(font instanceof FontMetadata,
                'Results should be FontMetadata instances');

    // Verify properties and types. This is partially redundant with an IDL
    // test but more domain-specific tests are be done.
    assert_equals(typeof font.postscriptName, 'string');
    assert_true(
      font.postscriptName.split('').every(c => ' ' <= c && c < '\x7f'),
      `postscriptName should be printable ASCII: "${font.postscriptName}"`
    );

    assert_equals(typeof font.fullName, 'string');
    assert_equals(typeof font.family, 'string');
    assert_equals(typeof font.style, 'string');

    assert_equals(typeof font.italic, 'boolean');

    assert_equals(typeof font.weight, 'number');
    assert_between_inclusive(font.weight, -1, 1);

    assert_equals(typeof font.stretch, 'number');
    assert_between_inclusive(font.stretch, -1, 1);
  });
});
