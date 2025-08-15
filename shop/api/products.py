from ninja import Router

router = Router()


@router.get("")
def products(request):
    return {"helo": "helo"}
