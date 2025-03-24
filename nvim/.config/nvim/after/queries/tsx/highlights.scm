;; extends
(jsx_element
  open_tag: (jsx_opening_element) @tag)

(jsx_element
  close_tag: (jsx_closing_element) @tag)

(jsx_self_closing_element) @tag

(jsx_attribute
  (property_identifier) @tag.attribute)

(jsx_text) @none

(jsx_expression) @expression
