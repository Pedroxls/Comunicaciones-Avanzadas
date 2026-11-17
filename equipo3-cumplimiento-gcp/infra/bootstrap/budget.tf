resource "google_billing_budget" "dev" {
  provider = google.facturacion

  billing_account = var.billing_account
  display_name    = "dev-cumplimiento"

  # Sin este filtro el presupuesto cuenta el gasto de toda la cuenta de cobro.
  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }

  amount {
    specified_amount {
      currency_code = var.budget_currency
      units         = tostring(var.budget_amount_usd)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }

  threshold_rules {
    threshold_percent = 0.9
  }

  threshold_rules {
    threshold_percent = 1.0
  }

  all_updates_rule {
    pubsub_topic   = google_pubsub_topic.presupuesto.id
    schema_version = "1.0"
  }

  depends_on = [
    google_project_service.apis,
    google_pubsub_topic_iam_member.presupuesto_publica,
  ]
}
