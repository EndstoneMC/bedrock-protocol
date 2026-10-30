#include "codec.h"

NB_MODULE(_native, module)
{
    using namespace bedrock::protocol::python;
    bindViews(module);
    bindNbt(module);
    bindGenerated(module);
}
