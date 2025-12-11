"""AWS automation helpers."""

from .s3_cleanup import run_cleanup as run_s3_cleanup
from .ec2_cleanup import run_ec2_cleanup
from .lambda_cleanup import run_lambda_cleanup
from .ebs_cleanup import run_ebs_cleanup
from .cloudwatch_cleanup import run_cloudwatch_cleanup
from .iam_cleanup import run_iam_cleanup
from .main import main
from .menu import interactive_menu

__all__ = [
    "run_s3_cleanup",
    "run_ec2_cleanup", 
    "run_lambda_cleanup",
    "run_ebs_cleanup",
    "run_cloudwatch_cleanup",
    "run_iam_cleanup",
    "main",
    "interactive_menu",
    "__version__"
]
__version__ = "0.1.0"
