// SPDX-License-Identifier: GPL-2.0-or-later
// Translate libmpg123 offsets without signed overflow or negative absolute seeks.
#pragma once

#include <cstdint>
#include <cstdio>
#include <limits>
#include <optional>
#include <sys/types.h>

constexpr std::optional<off_t>
Mpg123SeekOffset(std::uint64_t current, std::uint64_t size, bool known_size,
                off_t offset, int whence) noexcept
{
    std::uint64_t base;
    switch (whence) {
    case SEEK_SET: base = 0; break;
    case SEEK_CUR: base = current; break;
    case SEEK_END:
        if (!known_size)
            return std::nullopt;
        base = size;
        break;
    default: return std::nullopt;
    }

    constexpr off_t maximum = std::numeric_limits<off_t>::max();
    if (base > static_cast<std::uint64_t>(maximum))
        return std::nullopt;
    const auto position = static_cast<off_t>(base);
    if ((offset < 0 && offset < -position) ||
        (offset >= 0 && offset > maximum - position))
        return std::nullopt;
    return position + offset;
}
