# -*- coding: utf-8 -*-
"""
Placement Forecasting Module
Predict placement needs based on historical trends and data analysis
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import logging

_logger = logging.getLogger(__name__)


class PlacementForecast(models.Model):
    """Placement Forecasting"""
    _name = 'placement.forecast'
    _description = 'Placement Forecast'
    _order = 'forecast_date desc, create_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Forecast Name',
        required=True,
        default=lambda self: _('Forecast %s') % fields.Date.today().strftime('%Y-%m'),
    )
    
    # Forecast Parameters
    forecast_date = fields.Date(
        string='Forecast Date',
        default=fields.Date.today,
        required=True,
    )
    forecast_period = fields.Selection([
        ('1_month', '1 Month'),
        ('3_months', '3 Months'),
        ('6_months', '6 Months'),
        ('12_months', '12 Months'),
    ], string='Forecast Period', default='3_months', required=True)
    
    # Scope
    client_id = fields.Many2one(
        'tazweed.client',
        string='Client',
        help='Leave empty for all clients',
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        help='Leave empty for all departments',
    )
    job_category = fields.Char(
        string='Job Category',
        help='Filter by job category',
    )
    
    # Historical Data Analysis
    historical_months = fields.Integer(
        string='Historical Months to Analyze',
        default=12,
        help='Number of months of historical data to use',
    )
    
    # Forecast Results
    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
    ], string='Status', default='draft')
    
    # Predicted Values
    predicted_placements = fields.Integer(
        string='Predicted Placements',
        help='Expected number of new placements',
    )
    predicted_terminations = fields.Integer(
        string='Predicted Terminations',
        help='Expected number of placement endings',
    )
    predicted_net_change = fields.Integer(
        string='Predicted Net Change',
        compute='_compute_net_change',
        store=True,
    )
    
    # Confidence
    confidence_level = fields.Float(
        string='Confidence Level %',
        help='Statistical confidence in the forecast',
    )
    
    # Trend Analysis
    placement_trend = fields.Selection([
        ('increasing', 'Increasing'),
        ('stable', 'Stable'),
        ('decreasing', 'Decreasing'),
    ], string='Placement Trend')
    
    trend_percentage = fields.Float(
        string='Trend %',
        help='Percentage change in trend',
    )
    
    # Seasonality
    seasonality_factor = fields.Float(
        string='Seasonality Factor',
        help='Adjustment for seasonal patterns',
    )
    peak_months = fields.Char(
        string='Peak Months',
        help='Months with highest placement activity',
    )
    
    # Detailed Forecasts
    monthly_forecast_ids = fields.One2many(
        'placement.forecast.monthly',
        'forecast_id',
        string='Monthly Forecasts',
    )
    
    # Analysis Data
    analysis_data = fields.Text(
        string='Analysis Data (JSON)',
        help='Detailed analysis data in JSON format',
    )
    
    # Recommendations
    recommendations = fields.Html(
        string='Recommendations',
    )
    
    # Risk Factors
    risk_level = fields.Selection([
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
    ], string='Risk Level')
    risk_factors = fields.Text(
        string='Risk Factors',
    )
    
    # Audit
    calculated_date = fields.Datetime(
        string='Calculated Date',
    )
    calculated_by = fields.Many2one(
        'res.users',
        string='Calculated By',
    )
    approved_date = fields.Datetime(
        string='Approved Date',
    )
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
    )
    notes = fields.Text(string='Notes')

    @api.depends('predicted_placements', 'predicted_terminations')
    def _compute_net_change(self):
        for record in self:
            record.predicted_net_change = record.predicted_placements - record.predicted_terminations

    def action_calculate_forecast(self):
        """Calculate the placement forecast"""
        self.ensure_one()
        
        # Get historical data
        historical_data = self._get_historical_data()
        
        # Calculate trends
        trend_analysis = self._analyze_trends(historical_data)
        
        # Calculate seasonality
        seasonality = self._analyze_seasonality(historical_data)
        
        # Generate forecast
        forecast_results = self._generate_forecast(historical_data, trend_analysis, seasonality)
        
        # Generate monthly forecasts
        self._generate_monthly_forecasts(forecast_results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(forecast_results, trend_analysis)
        
        # Assess risk
        risk_assessment = self._assess_risk(forecast_results, trend_analysis)
        
        # Update record
        self.write({
            'state': 'calculated',
            'predicted_placements': forecast_results['placements'],
            'predicted_terminations': forecast_results['terminations'],
            'confidence_level': forecast_results['confidence'],
            'placement_trend': trend_analysis['trend'],
            'trend_percentage': trend_analysis['percentage'],
            'seasonality_factor': seasonality['factor'],
            'peak_months': seasonality['peak_months'],
            'analysis_data': json.dumps(forecast_results),
            'recommendations': recommendations,
            'risk_level': risk_assessment['level'],
            'risk_factors': risk_assessment['factors'],
            'calculated_date': fields.Datetime.now(),
            'calculated_by': self.env.uid,
        })
        
        return True

    def _get_historical_data(self):
        """Get historical placement data"""
        end_date = self.forecast_date
        start_date = end_date - relativedelta(months=self.historical_months)
        
        # Build domain
        domain = [
            ('date_start', '>=', start_date),
            ('date_start', '<=', end_date),
        ]
        
        if self.client_id:
            domain.append(('client_id', '=', self.client_id.id))
        
        # Get placements
        placements = self.env['tazweed.placement'].search(domain)
        
        # Group by month
        monthly_data = {}
        for placement in placements:
            month_key = placement.date_start.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'placements': 0,
                    'terminations': 0,
                }
            monthly_data[month_key]['placements'] += 1
            
            # Check for terminations
            if hasattr(placement, 'date_end') and placement.date_end:
                end_month = placement.date_end.strftime('%Y-%m')
                if end_month not in monthly_data:
                    monthly_data[end_month] = {
                        'placements': 0,
                        'terminations': 0,
                    }
                monthly_data[end_month]['terminations'] += 1
        
        return monthly_data

    def _analyze_trends(self, historical_data):
        """Analyze placement trends"""
        if not historical_data:
            return {
                'trend': 'stable',
                'percentage': 0.0,
                'slope': 0.0,
            }
        
        # Sort by month
        sorted_months = sorted(historical_data.keys())
        
        if len(sorted_months) < 3:
            return {
                'trend': 'stable',
                'percentage': 0.0,
                'slope': 0.0,
            }
        
        # Calculate trend using simple linear regression
        values = [historical_data[m]['placements'] for m in sorted_months]
        n = len(values)
        
        # Calculate averages
        avg_x = (n - 1) / 2
        avg_y = sum(values) / n
        
        # Calculate slope
        numerator = sum((i - avg_x) * (values[i] - avg_y) for i in range(n))
        denominator = sum((i - avg_x) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Determine trend
        if slope > 0.5:
            trend = 'increasing'
        elif slope < -0.5:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        # Calculate percentage change
        if values[0] > 0:
            percentage = ((values[-1] - values[0]) / values[0]) * 100
        else:
            percentage = 0
        
        return {
            'trend': trend,
            'percentage': round(percentage, 1),
            'slope': round(slope, 2),
        }

    def _analyze_seasonality(self, historical_data):
        """Analyze seasonal patterns"""
        if not historical_data:
            return {
                'factor': 1.0,
                'peak_months': '',
            }
        
        # Group by calendar month
        monthly_avg = {}
        for month_key, data in historical_data.items():
            calendar_month = int(month_key.split('-')[1])
            if calendar_month not in monthly_avg:
                monthly_avg[calendar_month] = []
            monthly_avg[calendar_month].append(data['placements'])
        
        # Calculate averages
        for month in monthly_avg:
            monthly_avg[month] = sum(monthly_avg[month]) / len(monthly_avg[month])
        
        # Find peak months
        if monthly_avg:
            overall_avg = sum(monthly_avg.values()) / len(monthly_avg)
            peak_months = [m for m, v in monthly_avg.items() if v > overall_avg * 1.2]
            
            month_names = {
                1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
                5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
                9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
            }
            peak_month_names = ', '.join([month_names[m] for m in sorted(peak_months)])
            
            # Calculate seasonality factor for current month
            current_month = self.forecast_date.month
            if current_month in monthly_avg and overall_avg > 0:
                factor = monthly_avg[current_month] / overall_avg
            else:
                factor = 1.0
        else:
            peak_month_names = ''
            factor = 1.0
        
        return {
            'factor': round(factor, 2),
            'peak_months': peak_month_names,
        }

    def _generate_forecast(self, historical_data, trend_analysis, seasonality):
        """Generate the forecast based on analysis"""
        # Get forecast period in months
        period_map = {
            '1_month': 1,
            '3_months': 3,
            '6_months': 6,
            '12_months': 12,
        }
        forecast_months = period_map.get(self.forecast_period, 3)
        
        # Calculate base values from historical data
        if historical_data:
            recent_months = sorted(historical_data.keys())[-6:]  # Last 6 months
            avg_placements = sum(historical_data[m]['placements'] for m in recent_months) / len(recent_months)
            avg_terminations = sum(historical_data[m]['terminations'] for m in recent_months) / len(recent_months)
        else:
            avg_placements = 5  # Default
            avg_terminations = 2
        
        # Apply trend adjustment
        trend_multiplier = 1.0
        if trend_analysis['trend'] == 'increasing':
            trend_multiplier = 1.0 + (trend_analysis['percentage'] / 100 / 12) * forecast_months
        elif trend_analysis['trend'] == 'decreasing':
            trend_multiplier = 1.0 + (trend_analysis['percentage'] / 100 / 12) * forecast_months
        
        # Apply seasonality
        seasonality_multiplier = seasonality['factor']
        
        # Calculate predictions
        predicted_placements = int(avg_placements * forecast_months * trend_multiplier * seasonality_multiplier)
        predicted_terminations = int(avg_terminations * forecast_months)
        
        # Calculate confidence based on data quality
        data_points = len(historical_data)
        if data_points >= 12:
            confidence = 85.0
        elif data_points >= 6:
            confidence = 70.0
        elif data_points >= 3:
            confidence = 55.0
        else:
            confidence = 40.0
        
        return {
            'placements': predicted_placements,
            'terminations': predicted_terminations,
            'confidence': confidence,
            'avg_monthly_placements': round(avg_placements, 1),
            'avg_monthly_terminations': round(avg_terminations, 1),
            'trend_multiplier': round(trend_multiplier, 2),
            'seasonality_multiplier': round(seasonality_multiplier, 2),
        }

    def _generate_monthly_forecasts(self, forecast_results):
        """Generate detailed monthly forecasts"""
        # Clear existing
        self.monthly_forecast_ids.unlink()
        
        period_map = {
            '1_month': 1,
            '3_months': 3,
            '6_months': 6,
            '12_months': 12,
        }
        forecast_months = period_map.get(self.forecast_period, 3)
        
        avg_placements = forecast_results['avg_monthly_placements']
        avg_terminations = forecast_results['avg_monthly_terminations']
        
        for i in range(forecast_months):
            month_date = self.forecast_date + relativedelta(months=i+1)
            
            # Apply some variation
            variation = 1.0 + (i * 0.02)  # Slight increase over time
            
            self.env['placement.forecast.monthly'].create({
                'forecast_id': self.id,
                'month': month_date.strftime('%Y-%m-01'),
                'predicted_placements': int(avg_placements * variation),
                'predicted_terminations': int(avg_terminations),
            })

    def _generate_recommendations(self, forecast_results, trend_analysis):
        """Generate actionable recommendations"""
        recommendations = []
        
        # Based on trend
        if trend_analysis['trend'] == 'increasing':
            recommendations.append(
                _('<li><strong>Expand Recruitment Pipeline:</strong> With an increasing trend of %.1f%%, '
                  'consider expanding your candidate sourcing channels to meet growing demand.</li>') % 
                trend_analysis['percentage']
            )
            recommendations.append(
                _('<li><strong>Build Talent Pool:</strong> Proactively build a talent pool for high-demand '
                  'positions to reduce time-to-fill.</li>')
            )
        elif trend_analysis['trend'] == 'decreasing':
            recommendations.append(
                _('<li><strong>Client Retention Focus:</strong> With a decreasing trend, focus on client '
                  'retention and expanding services with existing clients.</li>')
            )
            recommendations.append(
                _('<li><strong>Diversify Client Base:</strong> Consider targeting new industries or '
                  'geographic areas to offset the decline.</li>')
            )
        
        # Based on forecast
        if forecast_results['placements'] > 20:
            recommendations.append(
                _('<li><strong>Scale Operations:</strong> With %d predicted placements, ensure your '
                  'operations team is adequately staffed.</li>') % forecast_results['placements']
            )
        
        # Based on terminations
        if forecast_results['terminations'] > forecast_results['placements'] * 0.5:
            recommendations.append(
                _('<li><strong>Retention Strategy:</strong> High termination rate predicted. Review '
                  'placement quality and client satisfaction.</li>')
            )
        
        return '<ul>' + ''.join(recommendations) + '</ul>' if recommendations else ''

    def _assess_risk(self, forecast_results, trend_analysis):
        """Assess forecast risk level"""
        risk_factors = []
        risk_score = 0
        
        # Low confidence
        if forecast_results['confidence'] < 60:
            risk_factors.append(_('Low forecast confidence due to limited historical data'))
            risk_score += 2
        
        # Declining trend
        if trend_analysis['trend'] == 'decreasing' and trend_analysis['percentage'] < -20:
            risk_factors.append(_('Significant declining trend in placements'))
            risk_score += 2
        
        # High termination rate
        if forecast_results['terminations'] > forecast_results['placements'] * 0.7:
            risk_factors.append(_('High termination rate relative to new placements'))
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 3:
            level = 'high'
        elif risk_score >= 1:
            level = 'medium'
        else:
            level = 'low'
        
        return {
            'level': level,
            'factors': '\n'.join(risk_factors) if risk_factors else _('No significant risk factors identified'),
        }

    def action_approve(self):
        """Approve the forecast"""
        self.write({
            'state': 'approved',
            'approved_date': fields.Datetime.now(),
            'approved_by': self.env.uid,
        })
        return True

    def action_reset_to_draft(self):
        """Reset to draft"""
        self.state = 'draft'
        return True


class PlacementForecastMonthly(models.Model):
    """Monthly Forecast Details"""
    _name = 'placement.forecast.monthly'
    _description = 'Monthly Placement Forecast'
    _order = 'month'

    forecast_id = fields.Many2one(
        'placement.forecast',
        string='Forecast',
        required=True,
        ondelete='cascade',
    )
    month = fields.Date(
        string='Month',
        required=True,
    )
    month_name = fields.Char(
        string='Month Name',
        compute='_compute_month_name',
    )
    predicted_placements = fields.Integer(
        string='Predicted Placements',
    )
    predicted_terminations = fields.Integer(
        string='Predicted Terminations',
    )
    predicted_net = fields.Integer(
        string='Net Change',
        compute='_compute_net',
        store=True,
    )
    actual_placements = fields.Integer(
        string='Actual Placements',
        help='Fill in after the month ends for accuracy tracking',
    )
    actual_terminations = fields.Integer(
        string='Actual Terminations',
    )
    accuracy = fields.Float(
        string='Accuracy %',
        compute='_compute_accuracy',
        store=True,
    )

    @api.depends('month')
    def _compute_month_name(self):
        for record in self:
            if record.month:
                record.month_name = record.month.strftime('%B %Y')
            else:
                record.month_name = ''

    @api.depends('predicted_placements', 'predicted_terminations')
    def _compute_net(self):
        for record in self:
            record.predicted_net = record.predicted_placements - record.predicted_terminations

    @api.depends('predicted_placements', 'actual_placements')
    def _compute_accuracy(self):
        for record in self:
            if record.actual_placements and record.predicted_placements:
                diff = abs(record.actual_placements - record.predicted_placements)
                record.accuracy = max(0, 100 - (diff / record.predicted_placements * 100))
            else:
                record.accuracy = 0.0
