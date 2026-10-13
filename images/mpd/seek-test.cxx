// Exercise the exact helper compiled into the patched decoder on each native ABI.
#include "Mpg123SeekOffset.hxx"
#include <cassert>

int main()
{
    constexpr auto maximum = std::numeric_limits<off_t>::max();
    constexpr auto minimum = std::numeric_limits<off_t>::min();
    assert(Mpg123SeekOffset(100, 1000, true, 30, SEEK_SET) == 30);
    assert(Mpg123SeekOffset(100, 1000, true, 413, SEEK_CUR) == 513);
    assert(Mpg123SeekOffset(100, 1000, true, -4, SEEK_CUR) == 96);
    assert(Mpg123SeekOffset(100, 1000, true, 0, SEEK_CUR) == 100);
    assert(Mpg123SeekOffset(100, 1000, true, -128, SEEK_END) == 872);
    assert(Mpg123SeekOffset(100, 1000, true, 0, SEEK_END) == 1000);
    assert(!Mpg123SeekOffset(100, 0, false, 0, SEEK_END));
    assert(!Mpg123SeekOffset(100, 1000, true, -1, SEEK_SET));
    assert(!Mpg123SeekOffset(100, 1000, true, -101, SEEK_CUR));
    assert(!Mpg123SeekOffset(100, 1000, true, minimum, SEEK_CUR));
    assert(!Mpg123SeekOffset(maximum, maximum, true, 1, SEEK_CUR));
    assert(!Mpg123SeekOffset(0, maximum, true, 1, SEEK_END));
    assert(!Mpg123SeekOffset(static_cast<std::uint64_t>(maximum)+1, 0, false, 0, SEEK_CUR));
    assert(!Mpg123SeekOffset(0, 0, true, 0, 999));
    assert(Mpg123SeekOffset(maximum, maximum, true, -maximum, SEEK_CUR) == 0);
    assert(Mpg123SeekOffset(0, 0, true, maximum, SEEK_SET) == maximum);
}
