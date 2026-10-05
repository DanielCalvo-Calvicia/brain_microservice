from domain.entities.echo_guard import EchoGuard


def test_a_guard_with_no_margin_is_off_and_never_sees_an_echo() -> None:
    guard = EchoGuard(0)
    guard.robot_speaks(now=0.0, seconds=5.0)

    assert guard.enabled is False
    assert guard.hears_itself(1.0, 2.0) is False


def test_audio_captured_while_the_robot_spoke_is_its_echo() -> None:
    guard = EchoGuard(1.0)
    guard.robot_speaks(now=10.0, seconds=4.0)  # speaks from 10 to 14

    assert guard.hears_itself(11.0, 12.0) is True  # inside
    assert guard.hears_itself(8.0, 11.0) is True  # starts before it spoke, ends during
    assert guard.hears_itself(13.0, 20.0) is True  # starts during, ends after


def test_the_margin_covers_the_sound_dying_away_after_the_robot_stops() -> None:
    guard = EchoGuard(1.5)
    guard.robot_speaks(now=10.0, seconds=4.0)

    assert guard.hears_itself(15.0, 17.0) is True  # starts 1 s after it stopped: still echo
    assert guard.hears_itself(15.6, 17.0) is False  # starts after the margin: the user


def test_audio_before_the_robot_spoke_is_the_users() -> None:
    guard = EchoGuard(1.0)
    guard.robot_speaks(now=10.0, seconds=4.0)

    assert guard.hears_itself(2.0, 9.9) is False


def test_speech_sent_while_the_robot_is_still_speaking_queues_behind_it() -> None:
    guard = EchoGuard(0.5)
    guard.robot_speaks(now=10.0, seconds=4.0)  # until 14
    guard.robot_speaks(now=11.0, seconds=3.0)  # plays after: until 17

    assert guard.hears_itself(16.0, 16.5) is True
    assert guard.hears_itself(17.6, 19.0) is False


def test_separate_stretches_of_speech_are_each_remembered() -> None:
    guard = EchoGuard(0.5)
    guard.robot_speaks(now=10.0, seconds=2.0)
    guard.robot_speaks(now=30.0, seconds=2.0)

    assert guard.hears_itself(20.0, 25.0) is False  # the quiet between them
    assert guard.hears_itself(30.5, 31.0) is True


def test_old_speech_is_forgotten() -> None:
    guard = EchoGuard(1.0)
    guard.robot_speaks(now=0.0, seconds=2.0)
    guard.robot_speaks(now=500.0, seconds=2.0)

    assert guard.hears_itself(0.0, 1.0) is False
