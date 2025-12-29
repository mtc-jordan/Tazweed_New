# -*- coding: utf-8 -*-

# Base models first (no dependencies on other placement models)
from . import skill
from . import recruitment_stage
from . import client
from . import candidate

# Models that depend on base models
from . import job_order
from . import pipeline
from . import interview
from . import placement
from . import invoice

# Dashboard (abstract model)
from . import dashboard

# New Features - AI Matching, Video Interview, Offer Letter, Forecasting
from . import ai_candidate_matching
from . import video_interview
from . import offer_letter
from . import placement_forecasting
