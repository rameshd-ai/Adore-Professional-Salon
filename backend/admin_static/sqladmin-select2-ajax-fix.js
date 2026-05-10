/**
 * SQLAdmin stock main.js passes Select2 ajax.data with `this` not bound to the <select>,
 * so `name` is missing → backend 400 → "The results could not be loaded."
 * Re-init ajax Select2 with a closure over the element.
 */
(function ($) {
  'use strict';
  $(function () {
    $(':input[data-role="select2-ajax"]').each(function () {
      var $el = $(this);
      var url = $el.data('url');
      if (!url) return;

      if ($el.hasClass('select2-hidden-accessible')) {
        try {
          $el.select2('destroy');
        } catch (e) {
          /* ignore */
        }
      }

      var existingData = [];
      try {
        var raw = $el.attr('data-json');
        if (raw) existingData = JSON.parse(raw);
      } catch (e) {
        existingData = [];
      }

      var allowBlank = $el.attr('data-allow-blank') === '1';

      $el.select2({
        width: '100%',
        minimumInputLength: 1,
        placeholder: allowBlank ? ' ' : undefined,
        allowClear: allowBlank,
        ajax: {
          url: url,
          dataType: 'json',
          delay: 250,
          data: function (params) {
            return {
              name: $el.attr('name'),
              term: params.term,
            };
          },
          processResults: function (data) {
            return { results: data.results || [] };
          },
        },
      });

      for (var i = 0; i < existingData.length; i++) {
        var d = existingData[i];
        $el.append(new Option(d.text, d.id, true, true));
      }
      if (existingData.length) {
        $el.trigger('change');
      }
    });
  });
})(window.jQuery);
