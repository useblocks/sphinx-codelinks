#include <iostream>

// [[ One-line impl, OL_IMPL_1, impl ]]
void oneline_function()
{
    std::cout << "One-line need example" << std::endl;
}

/* @rst
.. impl:: RST Detailed Implementation
   :id: RST_IMPL_2
   :status: open

   This is a detailed need from an @rst block,
   coexisting with a one-line need.
@endrst */
void rst_function()
{
    std::cout << "RST block need example" << std::endl;
}
