odoo.define('theme_laze.megamenu_front_js', function (require) {
"use strict";

// Multi Level Mega Menu
$(document).on('mouseenter', 'header li.mm-mega-menu', function() {
    if ($(this).find(".mm-maga-main.mm-mega-cat-level").length > 0) {
        var $first_tab = $(this).find(".mm-category-level .mm-cat-level-1:eq(0)");
        $first_tab.find(".cat-level-title").addClass("active-li");
        $first_tab.find(".mm-cat-level-2").addClass("menu-active");
    }
});
$(document).on('mouseenter', '.mm-cat-level-1', function() {
    var $first_div = $(this).find('.cat-level-title');
    $first_div.addClass("active-li");
    $(this).find('.mm-cat-level-2').addClass("menu-active");
});
$(document).on('mouseleave', '.mm-cat-level-1', function() {
    var $first_div = $(this).find('.cat-level-title')
    $first_div.removeClass("active-li");
    $(this).find('.mm-cat-level-2').removeClass("menu-active");
});


});
