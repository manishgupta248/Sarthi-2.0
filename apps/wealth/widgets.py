from .networth import holding_attention, net_worth_summary, upcoming_events


def wealth_widget(request):
    summary = net_worth_summary()
    attention = summary["bank"]["attention"] + holding_attention(summary["rows"])
    return {
        "net_worth": summary["net_worth"],
        "assets": summary["assets_total"],
        "liabilities": summary["liabilities_total"],
        "attention_count": len(attention) + len(upcoming_events()),
    }
