import logging
from enum import Enum

from azure_devtools.ci_tools.github_tools import get_or_create_pull
from github import GithubException, UnknownObjectException

from swaggertosdk.SwaggerToSdkCore import get_context_tag_from_git_object
from swaggertosdk.SwaggerToSdkNewCLI import generate_sdk_from_git_object

_LOGGER = logging.getLogger("swaggertosdk.restapi.github_handler")

# How many context tag I authorize in a PR to accept it
_CONTEXT_TAG_LIMITS = 3

# SDK pr branch prefix
_SDK_PR_PREFIX = "restapi_auto_"
_SDK_PR_TEMPLATE = _SDK_PR_PREFIX+"{}"

# Default RestAPI branch
_DEFAULT_REST_BRANCH = "master"

# Default SDK branch
_DEFAULT_SDK_BRANCH = "master"

class SwaggerToSdkLabels(Enum):
    merged = "RestPRMerged", "0e8a16"
    refused = "RestPRRefused", "b60205"
    in_progress = "RestPRInProgress", "fbca04"
    service_pr = "ServicePR", "1d76db"

def get_or_create_label(sdk_pr_target_repo, label_enum):
    try:
        return sdk_pr_target_repo.get_label(label_enum.value[0])
    except UnknownObjectException:
        return sdk_pr_target_repo.create_label(*label_enum.value)

def safe_remove_label(issue, label):
    """Remove a label, does not fail if label was not there.
    """
    try:
        issue.remove_from_labels(label)
    except GithubException:
        pass

def manage_labels(issue, to_add=None, to_remove=None):
    if not to_add:
        to_add = []
    if not to_remove:
        to_remove = []
    for label_remove in to_remove:
        safe_remove_label(issue, get_or_create_label(issue.repository, label_remove))
    for label_add in to_add:
        try:
            issue.add_to_labels(get_or_create_label(issue.repository, label_add))
        except Exception: # pylint: disable=broad-except
            # Never fail is adding a label was impossible
            _LOGGER.warning("Unable to add label: %s", label_add)

def rest_pr_management(commentable, rest_pr, sdk_repo, sdk_tag, sdk_default_base=_DEFAULT_SDK_BRANCH):
    """What to do when something happen to a PR in the Rest repo.

    :param restpr: a PyGithub pull object
    :type restpr: github.PullRequest.PullRequest
    :param sdk_repo: a PyGithub repository
    :type sdk_repo: github.Repository.Repository
    :param str sdk_tag: repotag to use to filter SwaggerToSDK conf
    :param str sdk_default_base: Default SDK branch.
    """
    # Extract some metadata as variables
    rest_repo = rest_pr.base.repo
    # "repo" can be None if fork has been deleted.
    is_from_a_fork = rest_pr.head.repo is None or rest_pr.head.repo.full_name != rest_repo.full_name

    #
    # Work on context, ext if context is not good
    #
    context_tags = list(get_context_tag_from_git_object(rest_pr))
    if not context_tags:
        commentable.create_comment("### No generation context\nUnable to detect any generation context from this pull request.")
        return
    if len(context_tags) > _CONTEXT_TAG_LIMITS:
        commentable.create_comment(
            "### Too many contexts\nThis pull request contains more than {} contexts, SDK generation has been skipped. Contexts found:\n{}".format(
                _CONTEXT_TAG_LIMITS,
                "\n".join(["- {}".format(ctxt) for ctxt in context_tags])
            ))
        return

    #
    # Decide if this PR will use a context branch
    #
    # A RestPR will have a context branch if:
    # - This is from a fork. Local branch are considered of the context system.
    # - There is one context only. Too much complicated to handle two context branches.
    # - Base is master. If fork to a feature branch, keep that flow.
    is_pushed_to_context_branch = is_from_a_fork and len(context_tags) == 1 and rest_pr.base.ref == _DEFAULT_REST_BRANCH

    #
    # Compute the "head" of future SDK PR.
    #
    if is_from_a_fork:
        sdk_pr_head = _SDK_PR_TEMPLATE.format(rest_pr.number)
    else:
        sdk_pr_head = _SDK_PR_TEMPLATE.format(rest_pr.head.ref)

    #
    # Compute the "base" of future SDK PR.
    # "sdk_checkout_bases" is an ordered list of branchs to checkout, since this can be several
    # branches that derives from "master".
    # This are branches that SwaggerToSDK should have "push" permission. Do NOT add "master" or a protected
    # branch to that list.
    #
    sdk_checkout_bases = []
    if rest_pr.base.ref == _DEFAULT_REST_BRANCH:
        sdk_pr_base = sdk_default_base
    else:
        sdk_pr_base = _SDK_PR_TEMPLATE.format(rest_pr.base.ref)
        sdk_checkout_bases.append(sdk_pr_base)

    # In special case where I use context branch
    if is_pushed_to_context_branch:
        sdk_pr_base = _SDK_PR_TEMPLATE.format(context_tags[0])
        sdk_checkout_bases.insert(0, sdk_pr_base)

    #
    # Try to generate on "head", whatever the state of the PR.
    #
    generate_sdk_from_git_object(
        rest_pr,
        sdk_pr_head,
        None,  # We don't need repo id if it's a PR, infer from PR itself.
        sdk_repo.full_name,
        sdk_checkout_bases,
        fallback_base_branch_name=sdk_default_base,
        sdk_tag=sdk_tag
    )

    #
    # Try to create/get a SDK PR.
    #
    # There is a lot of reasons why a SDK PR could not exist even on a "close" event, so don't assume this exists.
    #
    try:
        sdk_pr = get_or_create_pull(
            sdk_repo,
            title='[AutoPR {}] {}'.format("/".join(context_tags), rest_pr.title),
            body="Created to sync {}".format(rest_pr.html_url),
            head=sdk_repo.owner.login+":"+sdk_pr_head,
            base=sdk_pr_base,
        )
    except Exception as err: # pylint: disable=broad-except
        _LOGGER.warning("Unable to create SDK PR: %s", err)
        commentable.create_comment("### Nothing to generate\nThe changes in this pull request did not result in any changes in the {} repository.".format(sdk_tag))
        return

    # Replace whatever message it was if we were able to do a PR
    commentable.create_comment("### Pull request created\nPull request {}#{} has been created for you based on the changes in this pull request.".format(sdk_repo.full_name, sdk_pr.number))

    #
    # Manage labels/state on this SDK PR.
    #
    sdk_pr_as_issue = sdk_repo.get_issue(sdk_pr.number)
    sdk_pr_merged = False
    if rest_pr.closed_at:  # If there is a date, this is closed
        head_ref = sdk_repo.get_git_ref("heads/{}".format(sdk_pr_head))
        if rest_pr.merged:
            manage_labels(sdk_pr_as_issue,
                          to_add=[SwaggerToSdkLabels.merged],
                          to_remove=[SwaggerToSdkLabels.in_progress])
            if sdk_pr.base.ref.startswith(_SDK_PR_PREFIX):
                try:
                    # Merge "single context PRs" automatically
                    sdk_pr.merge(merge_method="squash")
                    sdk_pr_merged = True
                    # Delete branch from merged PR
                    head_ref.delete()
                except Exception as err: # pylint: disable=broad-except
                    _LOGGER.warning("Was unable to merge: %s", err)
        else:
            manage_labels(sdk_pr_as_issue,
                          to_add=[SwaggerToSdkLabels.refused],
                          to_remove=[SwaggerToSdkLabels.in_progress])
            sdk_pr.edit(state="closed")
            # Delete branch from closed PR
            head_ref.delete()
    else:
        # Try to remove "refused", if it was re-opened
        manage_labels(sdk_pr_as_issue,
                      to_add=[SwaggerToSdkLabels.in_progress],
                      to_remove=[SwaggerToSdkLabels.refused])

    #
    # Extra work: if this was a context branch
    #
    if is_pushed_to_context_branch:
        try:
            context_pr = get_or_create_pull(
                sdk_repo,
                title='[AutoPR] {}'.format("/".join(context_tags)),
                body="Created to accumulate context: {}".format(context_tags[0]),
                head=sdk_repo.owner.login+":"+sdk_pr_base,
                base=sdk_default_base,
            )
        except Exception as err: # pylint: disable=broad-except
            _LOGGER.warning("Unable to create context PR: %s", err)
            return
        # We got the context PR!
        context_pr_as_issue = sdk_repo.get_issue(context_pr.number)
        manage_labels(context_pr_as_issue, [SwaggerToSdkLabels.service_pr])
        # Put a link into the SDK single PR
        if sdk_pr_merged:
            sdk_pr.create_issue_comment("This PR has been merged into {}".format(context_pr.html_url))
        # Update dashboar to talk about this PR
        msg = "Pull request {}#{} was created for you based on the changes in this pull request.\n".format(sdk_repo.full_name, sdk_pr.number)
        if sdk_pr.merged:
            title = "Pull request created and integrated"
            msg += "It has been merged into the service pull request located here: {}#{}".format(
                sdk_repo.full_name,
                context_pr.number
            )
        else:
            title = "Pull request created, pending integration"
            msg += "Once this pull request is merged, content will be added to the service pull request located here: {}#{}".format(
                sdk_repo.full_name,
                context_pr.number
            )
        commentable.create_comment("### {}\n{}".format(title, msg))

def clean_sdk_pr(rest_pr, sdk_repo):
    """Look for the SDK pr created by this RestPR and wipe it.
    """
    # Extract some metadata as variables
    rest_repo = rest_pr.base.repo
    # "repo" can be None if fork has been deleted.
    is_from_a_fork = rest_pr.head.repo is None or rest_pr.head.repo.full_name != rest_repo.full_name

    #
    # Compute the "head" of future SDK PR.
    #
    if is_from_a_fork:
        sdk_pr_head = _SDK_PR_TEMPLATE.format(rest_pr.number)
    else:
        sdk_pr_head = _SDK_PR_TEMPLATE.format(rest_pr.head.ref)

    #
    # Close all PRs from this branch
    #
    sdk_prs = list(sdk_repo.get_pulls(
        head=sdk_repo.owner.login+":"+sdk_pr_head,
    ))
    for sdk_pr in sdk_prs:
        sdk_pr.edit(state="closed")
        break
    else:
        return "Didn't find the SDK PR"

    #
    # Delete the branch.
    #
    head_ref = sdk_repo.get_git_ref("heads/{}".format(sdk_pr_head))
    head_ref.delete()
