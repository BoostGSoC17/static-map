//          Copyright Tom Westerhout 2017-2018.
// Distributed under the Boost Software License, Version 1.0.
//    (See accompanying file LICENSE_1_0.txt or copy at
//          http://www.boost.org/LICENSE_1_0.txt)

#include <boost/static_views/raw_view.hpp>
#include <string>

struct MySequence {
};

namespace boost {
namespace static_views {
    template <>
    struct sequence_traits<MySequence> {
        using size_type  = std::size_t;
        using index_type = std::size_t;
        using value_type = int;
        using reference  = int;

        static auto at(MySequence const&, std::size_t) -> int;
        static constexpr auto extent() noexcept -> std::ptrdiff_t
        {
            return 123;
        }
        static auto size(MySequence const&) noexcept -> std::string;
    };
} // namespace static_views
} // namespace boost

int main()
{
    MySequence seq{};
    // Pass a type that does not model the Sequence concept.
    // Reason: `size` function's return type is not convertible to
    // size_t.
    auto const view = boost::static_views::raw_view(seq);
}
