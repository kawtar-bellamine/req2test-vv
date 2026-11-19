Feature: HPU-200 unit controller, generated test specifications

  # ---- REQ-001
  Scenario: TC-001-01 start then response checked at the 500 ms deadline
    # verifies REQ-001, timing
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    And 50 ms elapse
    When the start button is pressed
    And 500 ms elapse
    Then k1 is True

  Scenario: TC-001-02 start while a fault is active: K1 never closes
    # verifies REQ-001, guard
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    And 50 ms elapse
    And inputs estop = True
    And 50 ms elapse
    And inputs estop = False
    And 50 ms elapse
    When the start button is pressed
    Then k1 stays False during 1000 ms

  # ---- REQ-002
  Scenario: TC-002-01 stop then response checked at the 200 ms deadline
    # verifies REQ-002, timing
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    When the stop button is pressed
    And 200 ms elapse
    Then k1 is False

  # ---- REQ-003
  Scenario: TC-003-01 estop then response checked at the 100 ms deadline
    # verifies REQ-003, timing
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs estop = True
    And 100 ms elapse
    Then k1 is False
    Then faults contains E01

  Scenario: TC-003-02 estop writes E01 with a time stamp in the fault log
    # verifies REQ-003, logging
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs estop = True
    And 100 ms elapse
    Then log contains E01

  # ---- REQ-004
  Scenario: TC-004-01 pressure at 245.0 bar for 2500 ms gives the response
    # verifies REQ-004, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pressure = 245.0
    And 2500 ms elapse
    Then k1 is False
    Then faults contains E12

  Scenario: TC-004-02 pressure exactly at the threshold 240.0 bar: no response
    # verifies REQ-004, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pressure = 240.0
    And 2500 ms elapse
    Then k1 is True
    Then faults does not contain E12

  Scenario: TC-004-03 pressure one step beyond the threshold (241.0 bar) gives the response
    # verifies REQ-004, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pressure = 241.0
    And 2500 ms elapse
    Then k1 is False
    Then faults contains E12

  Scenario: TC-004-04 pressure beyond the threshold for less than 2000 ms: no response yet, then response
    # verifies REQ-004, timing
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pressure = 245.0
    And 1800 ms elapse
    Then k1 is True
    Then faults does not contain E12
    And 400 ms elapse
    Then k1 is False
    Then faults contains E12

  # ---- REQ-005
  Scenario: TC-005-01 pressure at 145.0 bar for 10500 ms gives the response
    # verifies REQ-005, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pressure = 145.0
    And 10500 ms elapse
    Then warnings contains W03

  Scenario: TC-005-02 pressure exactly at the threshold 150.0 bar: no response
    # verifies REQ-005, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pressure = 150.0
    And 10500 ms elapse
    Then warnings does not contain W03

  Scenario: TC-005-03 pressure one step beyond the threshold (149.0 bar) gives the response
    # verifies REQ-005, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pressure = 149.0
    And 10500 ms elapse
    Then warnings contains W03

  Scenario: TC-005-04 pressure beyond the threshold for less than 10000 ms: no response yet, then response
    # verifies REQ-005, timing
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pressure = 145.0
    And 9800 ms elapse
    Then warnings does not contain W03
    And 400 ms elapse
    Then warnings contains W03

  Scenario: TC-005-05 pressure beyond the threshold with the motor stopped: no response
    # verifies REQ-005, guard
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    And 50 ms elapse
    And inputs pressure = 145.0
    And 10500 ms elapse
    Then warnings does not contain W03

  # ---- REQ-006
  Scenario: TC-006-01 temperature at 72.5 °C for 500 ms gives the response
    # verifies REQ-006, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs temperature = 72.5
    And 500 ms elapse
    Then k1 is False
    Then faults contains E34

  Scenario: TC-006-02 temperature exactly at the threshold 70.0 °C: no response
    # verifies REQ-006, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs temperature = 70.0
    And 500 ms elapse
    Then k1 is True
    Then faults does not contain E34

  Scenario: TC-006-03 temperature one step beyond the threshold (70.5 °C) gives the response
    # verifies REQ-006, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs temperature = 70.5
    And 500 ms elapse
    Then k1 is False
    Then faults contains E34

  # ---- REQ-007
  Scenario: TC-007-01 temperature at 47.5 °C for 500 ms gives the response
    # verifies REQ-007, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs temperature = 47.5
    And 500 ms elapse
    Then fan is True

  Scenario: TC-007-02 temperature exactly at the threshold 45.0 °C: no response
    # verifies REQ-007, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs temperature = 45.0
    And 500 ms elapse
    Then fan is False

  Scenario: TC-007-03 temperature one step beyond the threshold (45.5 °C) gives the response
    # verifies REQ-007, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs temperature = 45.5
    And 500 ms elapse
    Then fan is True

  # ---- REQ-008
  Scenario: TC-008-01 temperature at 37.5 °C for 500 ms gives the response
    # verifies REQ-008, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs temperature = 50.0
    And 50 ms elapse
    Then fan is True
    And inputs temperature = 37.5
    And 500 ms elapse
    Then fan is False

  Scenario: TC-008-02 temperature exactly at the threshold 40.0 °C: no response
    # verifies REQ-008, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs temperature = 50.0
    And 50 ms elapse
    Then fan is True
    And inputs temperature = 40.0
    And 500 ms elapse
    Then fan is True

  Scenario: TC-008-03 temperature one step beyond the threshold (39.5 °C) gives the response
    # verifies REQ-008, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs temperature = 50.0
    And 50 ms elapse
    Then fan is True
    And inputs temperature = 39.5
    And 500 ms elapse
    Then fan is False

  # ---- REQ-009
  Scenario: TC-009-01 level_ok then response checked at the 1000 ms deadline
    # verifies REQ-009, timing
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs level_ok = False
    And 1000 ms elapse
    Then k1 is False
    Then faults contains E40

  Scenario: TC-009-02 level_ok writes E40 with a time stamp in the fault log
    # verifies REQ-009, logging
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs level_ok = False
    And 1000 ms elapse
    Then log contains E40

  # ---- REQ-010
  Scenario: TC-010-01 pt_current at 3.1 mA for 500 ms gives the response
    # verifies REQ-010, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pt_current = 3.1
    And 500 ms elapse
    Then faults contains E21

  Scenario: TC-010-02 pt_current exactly at the threshold 3.6 mA: no response
    # verifies REQ-010, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pt_current = 3.6
    And 500 ms elapse
    Then faults does not contain E21

  Scenario: TC-010-03 pt_current one step beyond the threshold (3.5 mA) gives the response
    # verifies REQ-010, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pt_current = 3.5
    And 500 ms elapse
    Then faults contains E21

  # ---- REQ-011
  Scenario: TC-011-01 pt_current at 21.5 mA for 500 ms gives the response
    # verifies REQ-011, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pt_current = 21.5
    And 500 ms elapse
    Then faults contains E21

  Scenario: TC-011-02 pt_current exactly at the threshold 21.0 mA: no response
    # verifies REQ-011, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pt_current = 21.0
    And 500 ms elapse
    Then faults does not contain E21

  Scenario: TC-011-03 pt_current one step beyond the threshold (21.1 mA) gives the response
    # verifies REQ-011, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pt_current = 21.1
    And 500 ms elapse
    Then faults contains E21

  # ---- REQ-012
  Scenario: TC-012-01 phase_ok then response checked at the 500 ms deadline
    # verifies REQ-012, timing
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs phase_ok = False
    And 500 ms elapse
    Then faults contains E05

  Scenario: TC-012-02 phase_ok writes E05 with a time stamp in the fault log
    # verifies REQ-012, logging
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs phase_ok = False
    And 500 ms elapse
    Then log contains E05

  # ---- REQ-013
  Scenario: TC-013-01 with a latched fault, a start command never closes K1
    # verifies REQ-013, state
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    And 50 ms elapse
    And inputs estop = True
    And 50 ms elapse
    And inputs estop = False
    And 50 ms elapse
    When the start button is pressed
    Then k1 stays False during 700 ms

  Scenario: TC-013-02 a fault raised while running opens K1 and keeps it open after the cause is gone
    # verifies REQ-013, state
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs estop = True
    And 50 ms elapse
    And inputs estop = False
    And 50 ms elapse
    And 500 ms elapse
    When the start button is pressed
    And 700 ms elapse
    Then k1 is False

  # ---- REQ-014
  Scenario: TC-014-01 reset with the fault condition gone clears the fault
    # verifies REQ-014, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    And 50 ms elapse
    And inputs estop = True
    And 50 ms elapse
    And inputs estop = False
    And 50 ms elapse
    Then faults contains E01
    When the reset button is pressed
    And 50 ms elapse
    Then faults does not contain E01

  Scenario: TC-014-02 reset while the fault condition is still present keeps the fault
    # verifies REQ-014, guard
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    And 50 ms elapse
    And inputs estop = True
    And 50 ms elapse
    When the reset button is pressed
    Then faults contains E01
    Then faults stays E01 during 100 ms

  # ---- REQ-015
  Scenario: TC-015-01 temperature at 7.5 °C for 500 ms gives the response
    # verifies REQ-015, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    And 50 ms elapse
    And inputs temperature = 7.5
    And 500 ms elapse
    Then warnings contains W07
    When the start button is pressed
    And 600 ms elapse
    Then k1 is False

  Scenario: TC-015-02 temperature exactly at the threshold 10.0 °C: no response
    # verifies REQ-015, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    And 50 ms elapse
    And inputs temperature = 10.0
    And 500 ms elapse
    Then warnings does not contain W07
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True

  Scenario: TC-015-03 temperature one step beyond the threshold (9.5 °C) gives the response
    # verifies REQ-015, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    And 50 ms elapse
    And inputs temperature = 9.5
    And 500 ms elapse
    Then warnings contains W07
    When the start button is pressed
    And 600 ms elapse
    Then k1 is False

  # ---- REQ-016
  Scenario: TC-016-01 filter_hours at 505.0 h for 500 ms gives the response
    # verifies REQ-016, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs filter_hours = 505.0
    And 500 ms elapse
    Then warnings contains W20

  Scenario: TC-016-02 filter_hours exactly at the threshold 500.0 h: no response
    # verifies REQ-016, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs filter_hours = 500.0
    And 500 ms elapse
    Then warnings does not contain W20

  Scenario: TC-016-03 filter_hours one step beyond the threshold (501.0 h) gives the response
    # verifies REQ-016, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs filter_hours = 501.0
    And 500 ms elapse
    Then warnings contains W20

  # ---- REQ-017
  Scenario: TC-017-01 motor_current at 34.5 A for 5500 ms gives the response
    # verifies REQ-017, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs motor_current = 34.5
    And 5500 ms elapse
    Then k1 is False
    Then faults contains E07

  Scenario: TC-017-02 motor_current exactly at the threshold 32.0 A: no response
    # verifies REQ-017, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs motor_current = 32.0
    And 5500 ms elapse
    Then k1 is True
    Then faults does not contain E07

  Scenario: TC-017-03 motor_current one step beyond the threshold (32.5 A) gives the response
    # verifies REQ-017, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs motor_current = 32.5
    And 5500 ms elapse
    Then k1 is False
    Then faults contains E07

  Scenario: TC-017-04 motor_current beyond the threshold for less than 5000 ms: no response yet, then response
    # verifies REQ-017, timing
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs motor_current = 34.5
    And 4800 ms elapse
    Then k1 is True
    Then faults does not contain E07
    And 400 ms elapse
    Then k1 is False
    Then faults contains E07

  # ---- REQ-018
  Scenario: TC-018-01 a fault is written to the log with its time stamp
    # verifies REQ-018, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs estop = True
    And 50 ms elapse
    And inputs estop = False
    And 50 ms elapse
    Then log contains E01

  Scenario: TC-018-02 a second fault of another type is logged too
    # verifies REQ-018, logging
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs phase_ok = False
    And 50 ms elapse
    Then log contains E05

  # ---- REQ-019
  Scenario: TC-019-01 temperature at 62.5 °C for 500 ms gives the response
    # verifies REQ-019, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs temperature = 62.5
    And 500 ms elapse
    Then warnings contains W30

  Scenario: TC-019-02 temperature exactly at the threshold 60.0 °C: no response
    # verifies REQ-019, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs temperature = 60.0
    And 500 ms elapse
    Then warnings does not contain W30

  Scenario: TC-019-03 temperature one step beyond the threshold (60.5 °C) gives the response
    # verifies REQ-019, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs temperature = 60.5
    And 500 ms elapse
    Then warnings contains W30

  # ---- REQ-020
  Scenario: TC-020-01 pressure at 235.0 bar for 500 ms gives the response
    # verifies REQ-020, nominal
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pressure = 235.0
    And 500 ms elapse
    Then warnings contains W11

  Scenario: TC-020-02 pressure exactly at the threshold 230.0 bar: no response
    # verifies REQ-020, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pressure = 230.0
    And 500 ms elapse
    Then warnings does not contain W11

  Scenario: TC-020-03 pressure one step beyond the threshold (231.0 bar) gives the response
    # verifies REQ-020, boundary
    Given inputs pressure = 210.0, temperature = 35.0, pt_current = 12.4, motor_current = 24.0, filter_hours = 100.0, estop = False, level_ok = True, phase_ok = True
    When the start button is pressed
    And 600 ms elapse
    Then k1 is True
    And inputs pressure = 231.0
    And 500 ms elapse
    Then warnings contains W11
