// META: script=/resources/testdriver.js
// META: script=/resources/testdriver-vendor.js

'use strict';

promise_test(async t => {
  const update = await new Promise((resolve, reject) => {
    const observer = new ComputePressureObserver(resolve);
    t.add_cleanup(() => observer.stop());
    observer.observe().catch(reject);
  });

  assert_equals(typeof update.cpuUtilization, 'number');
  assert_equals(typeof update.cpuSpeed, 'number');
  assert_greater_than_equal(update.cpuUtilization, 0.0, "cpuUtilization range");
  assert_less_than_equal(update.cpuUtilization, 1.0, "cpuUtilization range");
  assert_greater_than_equal(update.cpuSpeed, 0.0, "cpuSpeed range");
  assert_less_than_equal(update.cpuSpeed, 1.0, "cpuSpeed range");
}, 'ComputePressureObserver calls its callback at least once');
