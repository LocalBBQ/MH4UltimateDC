// When the touch overlay shows at all: mh4u.ini's touch_screen, for playing on one screen. The
// touch overlay (touch_overlay, the custom layout) puts the touch screen over the game in a
// corner; quest_overlay cuts it down to the map in quests. touch_screen says when that corner is
// there: always (as before), only in quests, or only when the game needs the touch screen (the
// quest menu, a big panel such as the full map) and when the touch-screen key asks for it. No
// Azahar here (hooks.cpp gathers the state and hides the corner through the overlay's `hidden`),
// so it is tested on its own (tests/test_touch_screen.py).
#pragma once

#include <string>

namespace Port::TouchScreen {

/// The touch_screen option.
enum class Mode {
    Shown,   ///< "shown": the corner always shows (the touch overlay as before)
    Map,     ///< "map": only in quests (the map, as quest_overlay says) and when needed
    Hidden,  ///< "hidden": only when the game needs the touch screen, or the key asks for it
};

/// "shown" (also "on", "always"), "map" ("quests"), "hidden" ("off", "auto"), any case; anything
/// else is Shown, the touch overlay as it was before this option.
Mode Parse(std::string value);

/// The option's value for `mode`: "shown", "map" or "hidden".
const char* Name(Mode mode);

/// What decides whether the corner shows, once a frame.
struct State {
    Mode mode = Mode::Shown;
    bool in_quest = false;  ///< a quest is on (its playing state or its touch panels ran a moment ago)
    /// The quest menu or a big panel is up: the touch screen holds what the game needs now. Only
    /// counted in a quest, where the quest HUD's states mean something.
    bool touch_ui = false;
    bool peek = false;      ///< the touch-screen key asked for the touch screen (Peek)
    bool editing = false;   ///< the HUD layout editor is up: it shows the map and the target camera
};

/// Whether the corner is hidden now.
bool Hidden(const State& state);

/// The touch-screen key's ask for the touch screen outside what the mode shows. It stays until
/// the key is pressed again or a quest starts or ends, so that a peek in the village doesn't
/// carry into the hunt (or the other way round).
class Peek {
public:
    /// Once a frame: drops the peek when a quest starts or ends. Returns true when it did.
    bool Follow(bool in_quest);
    bool On() const { return on_; }
    void Set(bool on) { on_ = on; }

private:
    bool on_ = false;
    bool in_quest_ = false;
};

/// The touch-screen key, pressed.
struct KeyPress {
    /// false: the key does what it does with the corner always there (in quests, the map view's
    /// switch between the map and the whole touch screen, MapView::PressKey), which it always
    /// does with "shown" and in quests with "map"; the fields below then mean nothing.
    bool handled = false;
    bool peek = false;   ///< the peek after the press
    bool whole = false;  ///< the map view's switch after it: the whole touch screen, not the map
    std::string note;    ///< a short line for the screen: what the press did
};

/// The key in `state`, with the map view's switch at `whole` and `map_can_show` whether the map
/// view could show the map alone in this quest (MapView::Blocked is None or Switched). Outside
/// quests, or in a quest whose map can't show alone, a press toggles the peek. In a quest with
/// "hidden" and the map view available, presses go round: the map, the whole touch screen, hidden.
KeyPress PressKey(const State& state, bool whole, bool map_can_show);

} // namespace Port::TouchScreen
