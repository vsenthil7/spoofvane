// P25 — Billing. Current plan summary, the payment method on file, and invoice
// history with per-invoice status + download. Change-plan routes to Pricing.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';
import 'pricing_screen.dart';

class BillingScreen extends StatelessWidget {
  const BillingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Invoice>>(
      future: Api.instance.invoices(),
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final invoices = snap.data ?? [];
        return ListView(
          key: const Key('billing-list'),
          children: [
            const ScreenTitle('Billing',
                sub: 'Plan, payment method and invoices'),
            _planPanel(context),
            _paymentPanel(),
            _invoicesPanel(invoices),
          ],
        );
      },
    );
  }

  Widget _planPanel(BuildContext context) {
    return Panel(
      title: 'Current plan',
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Business',
                    style: TextStyle(
                        color: SvColors.text,
                        fontSize: 20,
                        fontWeight: FontWeight.bold)),
                const SizedBox(height: 2),
                const Text('\$1,999/mo · billed annually · renews 1 Jun 2026',
                    style: TextStyle(color: SvColors.muted, fontSize: 12)),
              ],
            ),
          ),
          OutlinedButton(
            key: const Key('billing-change-plan'),
            style: OutlinedButton.styleFrom(
                foregroundColor: SvColors.amber,
                side: const BorderSide(color: SvColors.amber)),
            onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const PricingScreen())),
            child: const Text('Change plan'),
          ),
        ],
      ),
    );
  }

  Widget _paymentPanel() {
    return Panel(
      title: 'Payment method',
      child: Row(
        children: [
          const Icon(Icons.credit_card, color: SvColors.cyan, size: 22),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Visa •••• 4242',
                    style: TextStyle(color: SvColors.text, fontSize: 13)),
                const Text('Expires 09/2028',
                    style: TextStyle(color: SvColors.faint, fontSize: 11)),
              ],
            ),
          ),
          TextButton(
            key: const Key('billing-update-card'),
            onPressed: () {},
            child: const Text('Update',
                style: TextStyle(color: SvColors.cyan, fontSize: 12)),
          ),
        ],
      ),
    );
  }

  Widget _invoicesPanel(List<Invoice> invoices) {
    return Panel(
      title: 'Invoices',
      child: Column(
        children: [
          const Row(children: [
            Expanded(flex: 3, child: HeaderLabel('INVOICE')),
            Expanded(flex: 3, child: HeaderLabel('DATE')),
            Expanded(flex: 2, child: HeaderLabel('AMOUNT')),
            Expanded(flex: 2, child: HeaderLabel('STATUS')),
            SizedBox(width: 90, child: HeaderLabel('')),
          ]),
          const Divider(color: SvColors.border),
          ...invoices.map(_invoiceRow),
        ],
      ),
    );
  }

  Widget _invoiceRow(Invoice inv) {
    final paid = inv.status == 'paid';
    return Padding(
      key: Key('invoice-row-${inv.id}'),
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Expanded(
              flex: 3,
              child: Text(inv.id,
                  style: const TextStyle(
                      color: SvColors.text,
                      fontFamily: 'monospace',
                      fontSize: 12))),
          Expanded(
              flex: 3,
              child: Text(fmtTime(inv.date),
                  style: const TextStyle(color: SvColors.muted, fontSize: 12))),
          Expanded(
              flex: 2,
              child: Text('\$${inv.amountUsd.toStringAsFixed(2)}',
                  style: const TextStyle(color: SvColors.text, fontSize: 12))),
          Expanded(
            flex: 2,
            child: Text(inv.status,
                style: TextStyle(
                    color: paid ? SvColors.benign : SvColors.amber,
                    fontSize: 12,
                    fontWeight: FontWeight.w600)),
          ),
          SizedBox(
            width: 90,
            child: TextButton(
              key: Key('invoice-download-${inv.id}'),
              onPressed: () {},
              style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  minimumSize: const Size(0, 32),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap),
              child: const Text('PDF',
                  style: TextStyle(color: SvColors.cyan, fontSize: 12)),
            ),
          ),
        ],
      ),
    );
  }
}
