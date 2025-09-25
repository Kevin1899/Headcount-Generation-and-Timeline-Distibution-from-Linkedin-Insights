# prompt_templates.py

USER_TEMPLATE: str = """
----------------  BEGIN DATA  ----------------
{insights_text}
----------------   END DATA   ----------------

Extract **all** of the following sections into one JSON object.
Keep **exact key order**. If a section isn’t present, use `null` (for single values) or `[]` (for lists).

1. company_profile {{
     employees_current: <int>,          # total headcount today
     hires_last_12_months: <int>,       # new hires past year
     growth_rate_percent_1y: <int>,     # % change vs. 1 year ago 
     attrition_percent_1y: <int>,       # % of headcount lost past year
     open_jobs: <int>,                  # active job postings
     industry: <string|null>,
     headquarters: <string|null>,
     founded_year: <int|null>,
     company_type: <string|null>
   }}

2. workforce_trend {{
     growth_6m_percent: <int>,          # % change vs. 6 months ago
     growth_1y_percent: <int>           # % change vs. 1 year ago
   }}

3. talent_flow {{
     hires: <int>,                      # hires past year
     departures: <int>,                 # departures past year
     net_change: <int>                  # hires - departures
   }}

4. top_functions_percent: [             # up to 5 entries
     {{ function: <string>, percent_employees: <int> }}
   ]

5. function_headcount: [                # up to 5 largest
     {{ function: <string>, headcount: <int> }}
   ]

6. locations: [                         # up to 10 entries
     {{
       location: <string>,
       employees: <int>,
       hires_1y: <int>,
       growth_1y_percent: <int>,
       percent_employees: <int>,
       attrition_percent: <int|null>
     }}
   ]

7. companies: {{                        # talent win/loss
     top_hire_sources: [                # up to 5
       {{ company: <string>, hires: <int> }}
     ],
     top_departure_destinations: [      # up to 5
       {{ company: <string>, departures: <int> }}
     ]
   }}

8. industries: [                        # up to 5 industries
     {{ industry: <string>, hires: <int>, departures: <int>, net_change: <int> }}
   ]

9. skills: {{
     top_skills: [                      # up to 10
       {{ skill: <string>, employees: <int>, hires_1y: <int>, growth_1y_percent: <int> }}
     ],
     fastest_growing: [                 # up to 10
       {{ skill: <string>, growth_1y_percent: <int> }}
     ]
   }}

10. education: {{
     degrees: [                        # all listed
       {{ degree: <string>, percent: <int> }}
     ],
     top_schools: [                    # up to 10
       {{ school: <string>, employees: <int>, hires_1y: <int>, growth_1y_percent: <int> }}
     ],
     fields_of_study: [                # up to 10
       {{ field: <string>, employees: <int>, hires_1y: <int>, growth_1y_percent: <int> }}
     ]
   }}

11. tenure: {{
     median_company_tenure_years: <float>,
     median_experience_years: <float>,
     high_tenure_functions: [          # up to 5
       {{ function: <string>, tenure_years: <float> }}
     ],
     low_tenure_functions: [           # up to 5
       {{ function: <string>, tenure_years: <float> }}
     ]
   }}

12. attrition_breakdown: {{
      by_function: [                   # up to 5
        {{ function: <string>, attrition_percent: <int> }}
      ],
      by_location: [                   # up to 5
        {{ location: <string>, attrition_percent: <int> }}
      ]
   }}

13. sample_profiles: [                  # optional; omit if noisy
     {{ name: <string>, title: <string>, location: <string> }}
   ]

Return **only** the JSON—no prose, no markdown.
"""


# prompt_templates.py

# USER_TEMPLATE: str = """
# ----------------  BEGIN DATA  ----------------
# {insights_text}
# ----------------   END DATA   ----------------

# Extract **all** of the following sections into one JSON object.
# Keep **exact key order**. If a section isn’t present, use `null` (for single values) or `[]` (for lists).

# 1. company_profile {{
#      employees_current: <int>,          # total headcount today
#      hires_last_12_months: <int>,       # new hires past year
#      growth_rate_percent_1y: <int>,     # % change vs. 1 year ago 
#      attrition_percent_1y: <int>,       # % of headcount lost past year
#      open_jobs: <int>,                  # active job postings
#      industry: <string|null>,
#      headquarters: <string|null>,
#      founded_year: <int|null>,
#      company_type: <string|null>
#    }}

# 2. workforce_trend {{
#      growth_6m_percent: <int>,          # % change vs. 6 months ago
#      growth_1y_percent: <int>           # % change vs. 1 year ago
#    }}

# 3. talent_flow {{
#      hires: <int>,                      # hires past year
#      departures: <int>,                 # departures past year
#      net_change: <int>                  # hires - departures
#    }}

# 4. top_functions_percent: [             
#      {{ function: <string>, percent_employees: <int> }}
#    ]

# 5. function_headcount: [               
#      {{ function: <string>, headcount: <int> }}
#    ]

# 6. locations: [                         
#      {{
#        location: <string>,
#        employees: <int>,
#        hires_1y: <int>,
#        growth_1y_percent: <int>,
#        percent_employees: <int>,
#        attrition_percent: <int|null>
#      }}
#    ]

# 7. companies: {{                        # talent win/loss
#      top_hire_sources: [                # up to 5
#        {{ company: <string>, hires: <int> }}
#      ],
#      top_departure_destinations: [      # up to 5
#        {{ company: <string>, departures: <int> }}
#      ]
#    }}

# 8. industries: [                        # up to 5 industries
#      {{ industry: <string>, hires: <int>, departures: <int>, net_change: <int> }}
#    ]

# 9. skills: {{
#      top_skills: [                     
#        {{ skill: <string>, employees: <int>, hires_1y: <int>, growth_1y_percent: <int> }}
#      ],
#      fastest_growing: [                
#        {{ skill: <string>, growth_1y_percent: <int> }}
#      ]
#    }}

# 10. education: {{
#      degrees: [                        # all listed
#        {{ degree: <string>, percent: <int> }}
#      ],
#      top_schools: [                    # up to 10
#        {{ school: <string>, employees: <int>, hires_1y: <int>, growth_1y_percent: <int> }}
#      ],
#      fields_of_study: [                # up to 10
#        {{ field: <string>, employees: <int>, hires_1y: <int>, growth_1y_percent: <int> }}
#      ]
#    }}

# 11. tenure: {{
#      median_company_tenure_years: <float>,
#      median_experience_years: <float>,
#      high_tenure_functions: [          # up to 5
#        {{ function: <string>, tenure_years: <float> }}
#      ],
#      low_tenure_functions: [           # up to 5
#        {{ function: <string>, tenure_years: <float> }}
#      ]
#    }}

# 12. attrition_breakdown: {{
#       by_function: [                   # up to 5
#         {{ function: <string>, attrition_percent: <int> }}
#       ],
#       by_location: [                   # up to 5
#         {{ location: <string>, attrition_percent: <int> }}
#       ]
#    }}

# 13. sample_profiles: [                  # optional; omit if noisy
#      {{ name: <string>, title: <string>, location: <string> }}
#    ]

# Return **only** the JSON—no prose, no markdown.
# """
