from .services import wealth_summary


def wealth_widget(request):
    summary = wealth_summary()
    return {
        "total": summary["total"],
        "account_count": len(summary["rows"]),
        "attention_count": len(summary["attention"]),
    }
