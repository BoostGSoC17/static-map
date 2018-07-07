//          Copyright Tom Westerhout 2017.
// Distributed under the Boost Software License, Version 1.0.
//    (See accompanying file LICENSE_1_0.txt or copy at
//          http://www.boost.org/LICENSE_1_0.txt)

#include "../../include/boost/static_views/detail/config.hpp"
#include "../../include/boost/static_views/detail/utils.hpp"
#include "../../include/boost/static_views/detail/invoke.hpp"
#include "../../include/boost/static_views/concepts.hpp"
#include "testing.hpp"
#include <utility>

constexpr auto foo() { return 10; }

struct bar {
    constexpr auto get() const noexcept { return 10; }
    constexpr auto operator()() const noexcept { return 10; }
    constexpr auto operator()(int const /*unused*/) const noexcept
    {
        return 10;
    }
};

auto test_nonmember()
{
    BOOST_TEST_EQ(boost::static_views::invoke(
                      [](auto&& p) noexcept { return p.second; },
                      std::make_pair(1, 2.0)),
        2.0);

    BOOST_TEST_EQ(boost::static_views::invoke(&foo), 10);
    BOOST_TEST_EQ(boost::static_views::invoke(foo), 10);
    BOOST_TEST_EQ(boost::static_views::invoke(bar{}), 10);

    constexpr auto r = boost::static_views::invoke(&foo);
    BOOST_TEST_EQ(r, 10);
}

auto test_member_function()
{
    BOOST_TEST_EQ(boost::static_views::invoke(&bar::get, bar{}), 10);

    constexpr auto r = boost::static_views::invoke(&bar::get, bar{});
    BOOST_TEST_EQ(r, 10);
}

auto test_data()
{
    BOOST_TEST_EQ(
        boost::static_views::invoke(
            &std::pair<int, double>::first, std::make_pair(1, 2.0)),
        1);
}

auto test_traits()
{
    BOOST_TEST_TRAIT_TRUE(
        (boost::static_views::is_invocable<decltype(&bar::get),
            bar const&>));
    BOOST_TEST_TRAIT_TRUE(
        (boost::static_views::is_invocable<decltype(test_data)>));
    BOOST_TEST_TRAIT_TRUE(
        (boost::static_views::is_invocable<bar, int>));
}

int main(void)
{
    test_nonmember();
    test_member_function();
    test_data();

    return boost::report_errors();
}
