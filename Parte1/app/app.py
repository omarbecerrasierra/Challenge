#!/usr/bin/env python3
import os

import aws_cdk as cdk



from cdk_proyect.cdk_proyect_stack import CdkProyectStack


app = cdk.App()
CdkProyectStack(app, "CdkProyectStack",
    description = "CDK Proyect Stack in Python, Fast API and Lambda",
    stack_name = "AnalyticsConceptStack"
    )

app.synth()
